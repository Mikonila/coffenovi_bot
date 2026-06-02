from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.catalog import Category

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


def _category_label(category: Category) -> str:
    emoji = CATEGORY_EMOJIS.get(category.name, "📋")
    return f"{category.name} {emoji}"


def categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=_category_label(category), callback_data=category.id)
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


def drink_navigation_keyboard(category_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
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
