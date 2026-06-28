from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.catalog import Category, InfoPage

CATEGORY_EMOJIS = {
    "Black Coffee": "☕",
    "Coffee & Milk": "☕🥛",
    "Latte": "☕🥛🥛",
    "Raf": "☕🥛🥛",
    "Iced Coffee": "🧊☕",
    "Not Coffee": "🥛",
    "Tea": "🍵",
    "Cold Drinks": "🧊🥤",
    "Cocktails": "🍹",
    "Syrups & Sauces": "🍯",
    "Cold Brew / Grind Size": "🫘",
}

INFO_BUTTONS = (
    ("📋 Чек-листы", "info:checklists"),
    ("🪣 Ген уборка", "info:dailycleaning"),
    ("⏳ Сроки хранения", "info:deadlines"),
)


def _category_label(category: Category) -> str:
    emoji = CATEGORY_EMOJIS.get(category.name, "📋")
    return f"{category.name} {emoji}"


def categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=_category_label(category), callback_data=category.id)
    for text, callback_data in INFO_BUTTONS:
        builder.button(text=text, callback_data=callback_data)
    builder.adjust(1)
    return builder.as_markup()


def drinks_keyboard(category: Category) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for drink in category.drinks:
        builder.button(text=drink.name, callback_data=drink.id)
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к разделам", callback_data="menu"),
    )
    builder.adjust(1)
    return builder.as_markup()


def drink_navigation_keyboard(
    category_id: str,
    *,
    drink_id: str,
    can_edit: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_edit:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🖼 Добавить фотографию",
                    callback_data=f"editor:add_photo:{drink_id}",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="🗑 Удалить фотографию",
                    callback_data=f"editor:remove_photo:{drink_id}",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="✏️ Изменить инфо",
                    callback_data=f"editor:edit_info:{drink_id}",
                )
            ]
        )
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к напиткам",
                    callback_data=f"card_back:{category_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Все разделы",
                    callback_data="card_menu",
                )
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def info_sections_keyboard(page: InfoPage) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for section in page.sections:
        builder.button(
            text=section.title,
            callback_data=f"info_section:{page.id}:{section.id}",
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к разделам", callback_data="menu"),
    )
    builder.adjust(1)
    return builder.as_markup()


def info_section_navigation_keyboard(page_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к разделам страницы",
                    callback_data=f"info:{page_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Все разделы",
                    callback_data="card_menu",
                )
            ],
        ]
    )
