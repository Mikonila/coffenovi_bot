from __future__ import annotations

import json
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from app.config import Settings
from app.translations import (
    display_drink_name,
    translate_category_name,
    translate_text,
)

SPREADSHEET_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "office": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "package": "http://schemas.openxmlformats.org/package/2006/relationships",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
TARGET_SHEET_NAME = "Drinks"
LAST_DRINK_ROW = 86


@dataclass(slots=True)
class Drink:
    id: str
    name: str
    category_id: str
    category_name: str
    row_number: int
    volume: str
    recipe: str
    method: str
    serving: str
    details: list[tuple[str, str]] = field(default_factory=list)
    image_ids: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    image_paths: list[Path] = field(default_factory=list)


@dataclass(slots=True)
class Category:
    id: str
    name: str
    row_number: int
    end_row: int
    drinks: list[Drink] = field(default_factory=list)


@dataclass(slots=True)
class Catalog:
    categories: list[Category]
    drinks_by_id: dict[str, Drink]
    image_registry: dict[str, Path]


REFERENCE_GRIND_TRANSLATIONS = {
    "Decaf": "Декаф",
    "Espresso": "Эспрессо",
    "Moka": "Мока",
    "v60": "V60",
    "Aeropress": "Аэропресс",
    "Turkish coffee": "Турецкий кофе",
    "HOOP": "Хуп",
    "FrenchPress": "Френч-пресс",
    "Filter/Batch": "Фильтр / батч",
}


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    shared = []
    text_tag = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
    for si in root:
        shared.append("".join(node.text or "" for node in si.iter(text_tag)))
    return shared


def _sheet_path_by_name(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}

    for sheet in workbook.find("main:sheets", SPREADSHEET_NS):
        if sheet.attrib.get("name") != sheet_name:
            continue
        rel_id = sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        return f"xl/{rel_map[rel_id]}"
    raise RuntimeError(f"Sheet {sheet_name!r} not found in workbook.")


def _parse_sheet_rows(archive: zipfile.ZipFile, sheet_path: str) -> dict[int, dict[str, str]]:
    shared = _shared_strings(archive)
    root = ET.fromstring(archive.read(sheet_path))
    rows: dict[int, dict[str, str]] = {}

    for row in root.findall(".//main:sheetData/main:row", SPREADSHEET_NS):
        row_number = int(row.attrib["r"])
        cell_values: dict[str, str] = {}
        for cell in row.findall("main:c", SPREADSHEET_NS):
            cell_ref = cell.attrib["r"]
            column = re.match(r"([A-Z]+)", cell_ref)
            if not column:
                continue

            value_node = cell.find("main:v", SPREADSHEET_NS)
            if value_node is None:
                inline = cell.find("main:is", SPREADSHEET_NS)
                if inline is None:
                    value = ""
                else:
                    value = "".join(
                        item.text or ""
                        for item in inline.iter(
                            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
                        )
                    )
            elif cell.attrib.get("t") == "s":
                value = shared[int(value_node.text)]
            else:
                value = value_node.text or ""

            cell_values[column.group(1)] = value.strip()

        if cell_values:
            rows[row_number] = cell_values

    return rows


def _sheet_image_rows(archive: zipfile.ZipFile, sheet_path: str) -> dict[int, list[str]]:
    root = ET.fromstring(archive.read(sheet_path))
    drawing = root.find("main:drawing", SPREADSHEET_NS)
    if drawing is None:
        return {}

    rel_id = drawing.attrib[
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    ]
    sheet_name = Path(sheet_path).name
    rels_path = f"xl/worksheets/_rels/{sheet_name}.rels"
    rels = ET.fromstring(archive.read(rels_path))
    drawing_target = None
    for rel in rels:
        if rel.attrib["Id"] == rel_id:
            drawing_target = rel.attrib["Target"]
            break
    if drawing_target is None:
        return {}

    drawing_path = f"xl/{drawing_target.replace('../', '')}"
    drawing_root = ET.fromstring(archive.read(drawing_path))

    drawing_rels_path = f"xl/drawings/_rels/{Path(drawing_path).name}.rels"
    drawing_rels: dict[str, str] = {}
    if drawing_rels_path in archive.namelist():
        rel_root = ET.fromstring(archive.read(drawing_rels_path))
        drawing_rels = {
            rel.attrib["Id"]: Path(rel.attrib["Target"]).name for rel in rel_root
        }

    per_row: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for anchor in drawing_root:
        picture = anchor.find("xdr:pic", SPREADSHEET_NS)
        from_node = anchor.find("xdr:from", SPREADSHEET_NS)
        if picture is None or from_node is None:
            continue

        row = int(from_node.find("xdr:row", SPREADSHEET_NS).text) + 1
        col = int(from_node.find("xdr:col", SPREADSHEET_NS).text) + 1
        blip = picture.find(".//a:blip", SPREADSHEET_NS)
        if blip is None:
            continue

        embed = blip.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
        ]
        image_name = drawing_rels.get(embed)
        if not image_name:
            continue
        per_row[row].append((col, image_name))

    result: dict[int, list[str]] = {}
    for row, items in per_row.items():
        unique: list[str] = []
        seen: set[str] = set()
        for _, image_name in sorted(items, key=lambda item: (item[0], item[1])):
            if image_name in seen:
                continue
            seen.add(image_name)
            unique.append(image_name)
        if unique:
            result[row] = unique

    return result


def _extract_images(
    archive: zipfile.ZipFile,
    destination: Path,
    image_ids: Iterable[str],
) -> dict[str, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    registry: dict[str, Path] = {}

    for image_id in sorted(set(image_ids)):
        archive_path = f"xl/media/{image_id}"
        if archive_path not in archive.namelist():
            continue

        target_path = destination / image_id
        if not target_path.exists():
            target_path.write_bytes(archive.read(archive_path))
        registry[image_id] = target_path

    return registry


def _nearest_images(
    row_number: int,
    start_row: int,
    end_row: int,
    row_images: dict[int, list[str]],
) -> list[str]:
    exact = row_images.get(row_number)
    if exact:
        return exact

    candidates = []
    for candidate_row, images in row_images.items():
        if start_row <= candidate_row <= end_row and images:
            candidates.append(
                (
                    abs(candidate_row - row_number),
                    len(images),
                    0 if candidate_row < row_number else 1,
                    candidate_row,
                    images,
                )
            )

    if not candidates:
        for candidate_row, images in row_images.items():
            if images:
                candidates.append(
                    (
                        abs(candidate_row - row_number),
                        len(images),
                        0 if candidate_row < row_number else 1,
                        candidate_row,
                        images,
                    )
                )

    if not candidates:
        return []

    return min(candidates)[-1]


def _load_cloudinary_cache(cache_path: Path) -> dict[str, str]:
    if not cache_path.exists():
        return {}

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return {str(key): str(value) for key, value in payload.items()}
    raise RuntimeError(f"Unexpected Cloudinary cache format in {cache_path}.")


def _append_reference_category(
    rows: dict[int, dict[str, str]],
    categories: list[Category],
) -> None:
    category = Category(
        id="category:reference",
        name="Cold Brew / Grind Size",
        row_number=88,
        end_row=106,
    )

    cold_brew_steps = "\n".join(
        translate_text(rows[row]["A"])
        for row in (89, 90, 91)
        if row in rows and rows[row].get("A")
    )
    category.drinks.append(
        Drink(
            id="drink:reference:cold-brew-preparation",
            name="Приготовление колд брю",
            category_id=category.id,
            category_name=category.name,
            row_number=89,
            volume="",
            recipe="",
            method="",
            serving="",
            details=[("Шаги", cold_brew_steps)],
        )
    )

    cold_brew_bottle = "\n".join(
        translate_text(rows[row]["A"])
        for row in (93, 94)
        if row in rows and rows[row].get("A")
    )
    category.drinks.append(
        Drink(
            id="drink:reference:cold-brew-bottle",
            name="Колд брю 220 мл",
            category_id=category.id,
            category_name=category.name,
            row_number=93,
            volume="",
            recipe="",
            method="",
            serving="",
            details=[("Рецепт", cold_brew_bottle)],
        )
    )

    for row_number in range(98, 107):
        values = rows.get(row_number, {})
        source_name = values.get("A", "").strip()
        grind_size = values.get("B", "").strip()
        if not source_name or not grind_size:
            continue

        translated_name = REFERENCE_GRIND_TRANSLATIONS.get(source_name, source_name)
        category.drinks.append(
            Drink(
                id=f"drink:reference:grind:{row_number}",
                name=f"Помол: {translated_name}",
                category_id=category.id,
                category_name=category.name,
                row_number=row_number,
                volume="",
                recipe="",
                method="",
                serving="",
                details=[
                    ("Тип", translated_name),
                    ("Размер помола", translate_text(grind_size)),
                ],
            )
        )

    categories.append(category)


def _apply_drink_text_fixes(drink: Drink, source_name: str) -> None:
    normalized_name = " ".join(source_name.strip().upper().split())
    if normalized_name != "CHERRY CREAM":
        return

    drink.recipe = "\n".join(
        [
            "8 шт (100 г) кубиков льда",
            "20 г - вишневый сироп",
            "40 г - жирные сливки (>30%)",
            "Основа на выбор:",
            "40 г - концентрат колд брю + 80 г воды",
            "или 150 г - холодный фильтр",
        ]
    )
    drink.method = "\n".join(
        [
            "1) Добавьте в питчер вишневый сироп и кофейную основу; если используете концентрат, добавьте воду. Тщательно перемешайте",
            "2) Взбейте сливки электрическим венчиком в течение 30 секунд",
            "3) Добавьте лед в стакан",
            "4) Влейте жидкость",
            "5) Влейте сливки",
        ]
    )


def load_catalog(settings: Settings) -> Catalog:
    with zipfile.ZipFile(settings.workbook_path) as archive:
        sheet_path = _sheet_path_by_name(archive, TARGET_SHEET_NAME)
        rows = _parse_sheet_rows(archive, sheet_path)
        row_images = _sheet_image_rows(archive, sheet_path)

        categories: list[Category] = []
        current_category: Category | None = None

        for row_number in sorted(rows):
            if row_number < 2 or row_number > LAST_DRINK_ROW:
                continue

            values = rows[row_number]
            name = values.get("A", "").strip()
            if not name:
                continue

            detail_present = any(values.get(column, "").strip() for column in ("B", "C", "D", "E"))
            if not detail_present:
                if current_category is not None:
                    current_category.end_row = row_number - 1
                current_category = Category(
                    id=f"category:{row_number}",
                    name=translate_category_name(name),
                    row_number=row_number,
                    end_row=LAST_DRINK_ROW,
                )
                categories.append(current_category)
                continue

            if current_category is None:
                continue

            drink = Drink(
                id=f"drink:{row_number}",
                name=display_drink_name(name),
                category_id=current_category.id,
                category_name=current_category.name,
                row_number=row_number,
                volume=translate_text(values.get("B", "")),
                recipe=translate_text(values.get("C", "")),
                method=translate_text(values.get("D", "")),
                serving=translate_text(values.get("E", "")),
            )
            _apply_drink_text_fixes(drink, name)
            current_category.drinks.append(drink)

        if current_category is not None:
            current_category.end_row = LAST_DRINK_ROW

        _append_reference_category(rows, categories)

        all_image_ids: set[str] = set()
        for category in categories:
            for drink in category.drinks:
                drink.image_ids = _nearest_images(
                    drink.row_number,
                    category.row_number,
                    category.end_row,
                    row_images,
                )
                all_image_ids.update(drink.image_ids)

        image_registry = _extract_images(archive, settings.assets_dir, all_image_ids)

    cloudinary_urls = _load_cloudinary_cache(settings.cloudinary_cache_path)
    drinks_by_id: dict[str, Drink] = {}
    for category in categories:
        for drink in category.drinks:
            drink.image_urls = [
                cloudinary_urls[image_id]
                for image_id in drink.image_ids
                if image_id in cloudinary_urls
            ]
            drink.image_paths = [
                image_registry[image_id]
                for image_id in drink.image_ids
                if image_id in image_registry
            ]
            drinks_by_id[drink.id] = drink

    return Catalog(
        categories=categories,
        drinks_by_id=drinks_by_id,
        image_registry=image_registry,
    )
