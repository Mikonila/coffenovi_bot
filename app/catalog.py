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
DRINK_CARD_FIELDS = ("volume", "recipe", "method", "serving")


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
    info_pages: dict[str, "InfoPage"]


@dataclass(slots=True)
class InfoSection:
    id: str
    title: str
    body: str


@dataclass(slots=True)
class InfoPage:
    id: str
    title: str
    sections: list[InfoSection] = field(default_factory=list)


REFERENCE_GRIND_TRANSLATIONS = {
    "Decaf": "Декаф",
    "Espresso": "Эспрессо",
    "Moka": "Мока",
    "v60": "V60",
    "Aeropress": "Аэропресс",
    "Turkish coffee": "Турецкий кофе",
    "HOOP": "Hoop",
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


def _card_storage_key(row_number: int) -> str:
    return f"drink:{row_number}"


def _manual_card_overrides() -> dict[str, dict[str, str]]:
    return {
        "CHERRY CREAM": {
            "recipe": "\n".join(
                [
                    "8 шт (100 г) кубиков льда",
                    "20 г - вишневый сироп",
                    "40 г - жирные сливки (>30%)",
                    "Основа на выбор:",
                    "40 г - концентрат колд брю + 80 г воды",
                    "или 150 г - холодный фильтр",
                ]
            ),
            "method": "\n".join(
                [
                    "1) Добавьте в питчер вишневый сироп и кофейную основу; если используете концентрат, добавьте воду. Тщательно перемешайте",
                    "2) Взбейте сливки электрическим венчиком в течение 30 секунд",
                    "3) Добавьте лед в стакан",
                    "4) Влейте жидкость",
                    "5) Влейте сливки",
                ]
            ),
        },
        "ORANGE POWDER": {
            "recipe": "\n".join(
                [
                    "250 г сахара",
                    "23 г - сушеная апельсиновая цедра",
                    "6 г - сушеная лимонная цедра",
                ]
            ),
            "method": "\n".join(
                [
                    "1) Добавьте сушеную апельсиновую и лимонную цедру, а также белый сахар в блендер.",
                    "2) Измельчите все на высокой скорости до однородности, периодически встряхивая стакан блендера.",
                ]
            ),
        },
        "LAVANDER POWDER": {
            "recipe": "\n".join(
                [
                    "280 г сахара",
                    "10 г - сушеная лаванда",
                    "3 г - соль",
                ]
            ),
            "method": "\n".join(
                [
                    "1) Добавьте сушеную лаванду, белый сахар и соль в блендер.",
                    "2) Измельчите все на высокой скорости до однородности, периодически встряхивая стакан блендера.",
                ]
            ),
        },
    }


def _build_translated_card(
    *,
    row_number: int,
    source_name: str,
    category_name: str,
    values: dict[str, str],
) -> dict[str, str | int]:
    payload: dict[str, str | int] = {
        "id": _card_storage_key(row_number),
        "row_number": row_number,
        "source_name": source_name,
        "name": display_drink_name(source_name),
        "category_name": category_name,
        "volume": translate_text(values.get("B", "")),
        "recipe": translate_text(values.get("C", "")),
        "method": translate_text(values.get("D", "")),
        "serving": translate_text(values.get("E", "")),
    }
    payload.update(_manual_card_overrides().get(" ".join(source_name.strip().upper().split()), {}))
    return payload


def _load_drink_cards(cards_path: Path) -> dict[str, dict[str, str]]:
    if not cards_path.exists():
        return {}

    payload = json.loads(cards_path.read_text(encoding="utf-8"))
    drinks_payload = payload.get("drinks", payload) if isinstance(payload, dict) else None
    if not isinstance(drinks_payload, dict):
        raise RuntimeError(f"Unexpected drink cards format in {cards_path}.")

    cards: dict[str, dict[str, str]] = {}
    for key, raw_card in drinks_payload.items():
        if not isinstance(raw_card, dict):
            continue

        card: dict[str, str] = {}
        card["id"] = str(raw_card.get("id", key)).strip()
        try:
            card["row_number"] = int(raw_card.get("row_number", 0))
        except (TypeError, ValueError):
            card["row_number"] = 0

        for field in ("source_name", "name", "category_name", *DRINK_CARD_FIELDS):
            value = raw_card.get(field, "")
            if value is None:
                card[field] = ""
            elif isinstance(value, str):
                card[field] = value.strip()
            else:
                card[field] = str(value).strip()
        cards[str(key)] = card
    return cards


def _append_manual_cards(
    categories: list[Category],
    stored_cards: dict[str, dict[str, str]],
    existing_ids: set[str],
) -> None:
    categories_by_name = {category.name: category for category in categories}
    for card_id, card in sorted(
        stored_cards.items(),
        key=lambda item: (int(item[1].get("row_number", 0)), item[0]),
    ):
        if card_id in existing_ids:
            continue

        category_name = card.get("category_name", "")
        category = categories_by_name.get(category_name)
        if category is None:
            continue

        category.drinks.append(
            Drink(
                id=card_id,
                name=card.get("name", "") or card.get("source_name", "") or card_id,
                category_id=category.id,
                category_name=category.name,
                row_number=int(card.get("row_number", 0)),
                volume=card.get("volume", ""),
                recipe=card.get("recipe", ""),
                method=card.get("method", ""),
                serving=card.get("serving", ""),
            )
        )

    for category in categories:
        category.drinks.sort(key=lambda drink: (drink.row_number, drink.id))


def _normalize_multiline_text(value: str) -> str:
    lines = []
    for raw_line in value.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        lines.append(line)
    return "\n".join(lines)


def _format_task(number: str, text: str) -> str:
    task_text = _normalize_multiline_text(text)
    if not task_text:
        return ""
    number = number.strip()
    if number:
        return f"{number} {task_text}"
    return task_text


def _slugify_info_title(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or fallback


def _format_daily_cleaning_section(tasks: str, comments: str) -> str:
    parts = []
    tasks_text = _normalize_multiline_text(tasks)
    comments_text = _normalize_multiline_text(comments)
    if tasks_text:
        parts.append(tasks_text)
    if comments_text:
        parts.append(f"Комментарий:\n{comments_text}")
    return "\n\n".join(parts)


def _sentence_case_title(value: str) -> str:
    normalized = " ".join(value.strip().split()).lower()
    if not normalized:
        return ""
    return normalized[0].upper() + normalized[1:]


DEADLINE_SECTION_TITLES = {
    "Pastries": "Выпечка",
    "Frezzer": "Заморозка",
    "Milk": "Молоко",
    "SAUCES": "Соусы",
    "SOFT DRINKS": "Безалкогольные напитки",
    "WINE": "Вино",
}

DEADLINE_ITEM_TITLES = {
    "Classic croissant": "Классический круассан",
    "Choco croissant": "Шоколадный круассан",
    "Сiabatta Sandwich": "Сэндвич на чиабатте",
    "Prosciutto croissant": "Круассан с прошутто",
    "Donut": "Донат",
    "PannaCotta": "Панна-котта",
    "Tiramisu": "Тирамису",
    "Cheesecake": "Чизкейк",
    "HoneyCake": "Медовик",
    "Carrot cake": "Морковный торт",
    "Brownie": "Брауни",
    "Banana bread": "Банановый хлеб",
    "Cinabon": "Синнабон",
    "LemonCake": "Лимонный кекс",
    "Coockies": "Печенье",
    "ChikenSalad": "Куриный салат",
    "FruitSalad": "Фруктовый салат",
    "Cold brew bottle": "Колд брю в бутылке",
    "Cold brew concentrate": "Концентрат колд брю",
    "Regular milk": "Обычное молоко",
    "Cream": "Сливки",
    "Plant based milk": "Растительное молоко",
    "Lactose free": "Безлактозное молоко",
    "Salted caramel": "Соленая карамель",
    "Caramel syrup(Bumble)": "Карамельный сироп (Bumble)",
    "Singapore": "Singapore",
    "Simple syrup": "Сахарный сироп",
    "Halva syrup": "Халвенный сироп",
    "Maple syrup": "Кленовый сироп",
    "Mastard sauce": "Горчичный соус",
    "Condensed milk": "Сгущенное молоко",
    "Blackcurrant Sauce": "Соус из черной смородины",
    "Sea buckthorn Sauce": "Облепиховый соус",
    "Sparkling Water 0,25": "Газированная вода 0,25",
    "Freshly squized orange juice": "Свежевыжатый апельсиновый сок",
    "Orange juice": "Апельсиновый сок",
    "Blackcurrant 320ml": "Черная смородина 320 мл",
    "Sea buckthorn 320ml": "Облепиха 320 мл",
    "Sparkling Wine": "Игристое вино",
}

DEADLINE_COMMENT_TRANSLATIONS = {
    "after cooked": "после приготовления",
    "after cooked / in fridge": "после приготовления / в холодильнике",
    "after cooked / in box": "после приготовления / в боксе",
    "after defrosted / in fridge": "после разморозки / в холодильнике",
    "after opened": "после открытия",
    "after opened / in fridge": "после открытия / в холодильнике",
    "try before writed off": "проверить вкус перед списанием",
}


def _translate_deadline_period(value: str) -> str:
    text = " ".join(value.strip().split())
    replacements = {
        "1 day": "1 день",
        "3 day": "3 дня",
        "5 days": "5 дней",
        "7 days": "7 дней",
        "14 days": "14 дней",
        "3 days in fridge": "3 дня в холодильнике",
        "7 days in fridge": "7 дней в холодильнике",
        "48 hours(2d)": "48 часов (2 дня)",
        "72 hours (3d)": "72 часа (3 дня)",
        "96 hours (4d)": "96 часов (4 дня)",
        "120 hours (5d)": "120 часов (5 дней)",
    }
    return replacements.get(text, text)


def _translate_deadline_comment(value: str) -> str:
    text = " ".join(value.strip().split()).lower()
    return DEADLINE_COMMENT_TRANSLATIONS.get(text, value.strip())


def _build_deadlines_body(items: list[tuple[str, str, str]]) -> str:
    lines = []
    for name, period, comment in items:
        translated_name = DEADLINE_ITEM_TITLES.get(name.strip(), name.strip())
        translated_period = _translate_deadline_period(period)
        translated_comment = _translate_deadline_comment(comment)
        line = f"• {translated_name} — {translated_period}"
        if translated_comment:
            line += f" ({translated_comment})"
        lines.append(line)
    return "\n".join(lines)


def _load_info_pages(archive: zipfile.ZipFile) -> dict[str, InfoPage]:
    pages: dict[str, InfoPage] = {}

    checklist_rows = _parse_sheet_rows(archive, _sheet_path_by_name(archive, "CheckLists"))
    checklist_sections: list[InfoSection] = []
    current_title = ""
    current_tasks: list[str] = []
    section_index = 0
    for row_number in sorted(checklist_rows):
        values = checklist_rows[row_number]
        column_a = values.get("A", "").strip()
        column_b = values.get("B", "").strip()
        column_c = values.get("C", "").strip()
        column_d = values.get("D", "").strip()

        if column_a and not any((column_b, column_c, column_d)):
            if current_title and current_tasks:
                section_index += 1
                checklist_sections.append(
                    InfoSection(
                        id=str(section_index),
                        title=current_title,
                        body="\n".join(current_tasks),
                    )
                )
            current_title = _sentence_case_title(column_a)
            current_tasks = []
            continue

        if column_b and column_b.upper() != "ЗАДАЧА":
            task = _format_task(column_a, column_b)
            if task:
                current_tasks.append(task)

    if current_title and current_tasks:
        section_index += 1
        checklist_sections.append(
            InfoSection(id=str(section_index), title=current_title, body="\n".join(current_tasks))
        )
    pages["checklists"] = InfoPage(id="checklists", title="Чек-листы", sections=checklist_sections)

    cleaning_rows = _parse_sheet_rows(archive, _sheet_path_by_name(archive, "DailyCleaning"))
    cleaning_sections: list[InfoSection] = []
    for row_number in sorted(cleaning_rows):
        values = cleaning_rows[row_number]
        day = values.get("A", "").strip()
        tasks = values.get("B", "").strip()
        comments = values.get("C", "").strip()
        if not day or day in {"ГЕН УБОРКА ХН"} or tasks == "ЗАДАЧА":
            continue
        cleaning_sections.append(
            InfoSection(
                id=_slugify_info_title(day, str(row_number)),
                title=day,
                body=_format_daily_cleaning_section(tasks, comments),
            )
        )
    pages["dailycleaning"] = InfoPage(
        id="dailycleaning",
        title="Ген уборка",
        sections=cleaning_sections,
    )

    deadline_rows = _parse_sheet_rows(archive, _sheet_path_by_name(archive, "Deadlines"))
    deadline_sections: list[InfoSection] = []
    current_deadline_title = ""
    current_items: list[tuple[str, str, str]] = []
    section_index = 0
    for row_number in sorted(deadline_rows):
        values = deadline_rows[row_number]
        column_a = values.get("A", "").strip()
        column_b = values.get("B", "").strip()
        column_c = values.get("C", "").strip()
        if not column_a:
            continue

        if column_a == "Name":
            continue

        if column_a and not column_b and not column_c:
            if current_deadline_title and current_items:
                section_index += 1
                deadline_sections.append(
                    InfoSection(
                        id=str(section_index),
                        title=DEADLINE_SECTION_TITLES.get(current_deadline_title, current_deadline_title),
                        body=_build_deadlines_body(current_items),
                    )
                )
            current_deadline_title = column_a
            current_items = []
            continue

        if current_deadline_title and column_b:
            current_items.append((column_a, column_b, column_c))

    if current_deadline_title and current_items:
        section_index += 1
        deadline_sections.append(
            InfoSection(
                id=str(section_index),
                title=DEADLINE_SECTION_TITLES.get(current_deadline_title, current_deadline_title),
                body=_build_deadlines_body(current_items),
            )
        )
    pages["deadlines"] = InfoPage(
        id="deadlines",
        title="Сроки хранения",
        sections=deadline_sections,
    )

    return pages


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

def export_drink_cards(settings: Settings) -> dict[str, dict[str, str | int]]:
    with zipfile.ZipFile(settings.workbook_path) as archive:
        sheet_path = _sheet_path_by_name(archive, TARGET_SHEET_NAME)
        rows = _parse_sheet_rows(archive, sheet_path)

    cards: dict[str, dict[str, str | int]] = {}
    current_category_name = ""
    for row_number in sorted(rows):
        if row_number < 2 or row_number > LAST_DRINK_ROW:
            continue

        values = rows[row_number]
        source_name = values.get("A", "").strip()
        if not source_name:
            continue

        detail_present = any(values.get(column, "").strip() for column in ("B", "C", "D", "E"))
        if not detail_present:
            current_category_name = translate_category_name(source_name)
            continue

        if not current_category_name:
            continue

        card = _build_translated_card(
            row_number=row_number,
            source_name=source_name,
            category_name=current_category_name,
            values=values,
        )
        cards[str(card["id"])] = card

    return cards


def load_catalog(settings: Settings) -> Catalog:
    stored_cards = _load_drink_cards(settings.drink_cards_path)
    existing_ids: set[str] = set()
    with zipfile.ZipFile(settings.workbook_path) as archive:
        sheet_path = _sheet_path_by_name(archive, TARGET_SHEET_NAME)
        rows = _parse_sheet_rows(archive, sheet_path)
        row_images = _sheet_image_rows(archive, sheet_path)
        info_pages = _load_info_pages(archive)

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

            stored_card = stored_cards.get(_card_storage_key(row_number), {})
            if stored_card:
                card_name = stored_card.get("name") or display_drink_name(name)
                volume = stored_card.get("volume", "")
                recipe = stored_card.get("recipe", "")
                method = stored_card.get("method", "")
                serving = stored_card.get("serving", "")
            else:
                default_card = _build_translated_card(
                    row_number=row_number,
                    source_name=name,
                    category_name=current_category.name,
                    values=values,
                )
                card_name = str(default_card["name"])
                volume = str(default_card["volume"])
                recipe = str(default_card["recipe"])
                method = str(default_card["method"])
                serving = str(default_card["serving"])

            drink = Drink(
                id=_card_storage_key(row_number),
                name=card_name,
                category_id=current_category.id,
                category_name=current_category.name,
                row_number=row_number,
                volume=volume,
                recipe=recipe,
                method=method,
                serving=serving,
            )
            existing_ids.add(drink.id)
            current_category.drinks.append(drink)

        if current_category is not None:
            current_category.end_row = LAST_DRINK_ROW

        _append_manual_cards(categories, stored_cards, existing_ids)
        _append_reference_category(rows, categories)

        all_image_ids: set[str] = set()
        for category in categories:
            for drink in category.drinks:
                drink.image_ids = row_images.get(drink.row_number, [])
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
        info_pages=info_pages,
    )
