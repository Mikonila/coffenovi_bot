from __future__ import annotations

import asyncio
from html import escape

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message

from app.catalog import Catalog, Category, Drink, load_catalog
from app.cloudinary import sync_catalog_images
from app.config import Settings, load_settings
from app.keyboards import categories_keyboard, drink_navigation_keyboard, drinks_keyboard

router = Router()


def _is_admin(user_id: int | None, settings: Settings) -> bool:
    return user_id is not None and user_id in settings.admin_user_ids


async def _deny_message(message: Message) -> None:
    await message.answer("У вас нет доступа к этому боту.")


async def _deny_callback(callback: CallbackQuery) -> None:
    await callback.answer("У вас нет доступа к этому боту.", show_alert=True)


def _format_drink_message(drink: Drink) -> str:
    lines = [f"<b>{escape(drink.name)}</b>"]
    if drink.details:
        for label, value in drink.details:
            if value:
                lines.append(f"<b>{escape(label)}:</b>\n{escape(value)}")
        return "\n\n".join(lines)

    if drink.volume:
        lines.append(f"<b>Объем:</b>\n{escape(drink.volume)}")
    if drink.recipe:
        lines.append(f"<b>Состав:</b>\n{escape(drink.recipe)}")
    if drink.method:
        lines.append(f"<b>Приготовление:</b>\n{escape(drink.method)}")
    if drink.serving:
        lines.append(f"<b>Подача:</b>\n{escape(drink.serving)}")
    return "\n\n".join(lines)


def _resolve_media_items(drink: Drink) -> list[str | FSInputFile]:
    if drink.image_urls:
        return drink.image_urls
    return [FSInputFile(str(path)) for path in drink.image_paths]


def _category_by_id(catalog: Catalog, category_id: str) -> Category | None:
    return next((category for category in catalog.categories if category.id == category_id), None)


async def _send_drink_details(message: Message, drink: Drink) -> None:
    media_items = _resolve_media_items(drink)
    if len(media_items) == 1:
        await message.answer_photo(photo=media_items[0])
    elif len(media_items) > 1:
        media_group = [InputMediaPhoto(media=item) for item in media_items]
        await message.answer_media_group(media=media_group)

    await message.answer(
        _format_drink_message(drink),
        reply_markup=drink_navigation_keyboard(drink.category_id),
    )


async def _send_categories_message(message: Message, catalog: Catalog) -> None:
    await message.answer(
        "Выберите раздел с напитками:",
        reply_markup=categories_keyboard(catalog.categories),
    )


async def _send_category_drinks_message(
    message: Message,
    catalog: Catalog,
    category_id: str,
) -> None:
    category = _category_by_id(catalog, category_id)
    if category is None:
        return

    await message.answer(
        f"Раздел: <b>{escape(category.name)}</b>\nВыберите напиток:",
        reply_markup=drinks_keyboard(category),
    )


async def _show_categories(
    callback: CallbackQuery,
    catalog: Catalog,
    *,
    target_message_id: int | None = None,
) -> None:
    if callback.message is None:
        return

    if target_message_id is None:
        await _safe_edit_message_text(
            callback,
            text="Выберите раздел с напитками:",
            reply_markup=categories_keyboard(catalog.categories),
        )
        return

    await _safe_edit_message_text(
        callback,
        text="Выберите раздел с напитками:",
        reply_markup=categories_keyboard(catalog.categories),
        target_message_id=target_message_id,
    )


async def _show_category_drinks(
    callback: CallbackQuery,
    catalog: Catalog,
    category_id: str,
    *,
    target_message_id: int | None = None,
) -> None:
    if callback.message is None:
        return

    category = _category_by_id(catalog, category_id)
    if category is None:
        return

    text = f"Раздел: <b>{escape(category.name)}</b>\nВыберите напиток:"
    markup = drinks_keyboard(category)

    if target_message_id is None:
        await _safe_edit_message_text(callback, text=text, reply_markup=markup)
        return

    await _safe_edit_message_text(
        callback,
        text=text,
        reply_markup=markup,
        target_message_id=target_message_id,
    )


async def _safe_edit_message_text(
    callback: CallbackQuery,
    *,
    text: str,
    reply_markup,
    target_message_id: int | None = None,
) -> None:
    if callback.message is None:
        return

    try:
        if target_message_id is None:
            await callback.message.edit_text(text, reply_markup=reply_markup)
            return

        await callback.bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=target_message_id,
            text=text,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return
        raise


@router.message(CommandStart())
async def start_handler(message: Message, catalog: Catalog, settings: Settings) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None, settings):
        await _deny_message(message)
        return
    await _send_categories_message(message, catalog)


@router.callback_query(F.data == "menu")
async def menu_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    await _show_categories(callback, catalog)


@router.callback_query(F.data == "card_menu")
async def card_menu_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    if callback.message is None:
        return
    await _send_categories_message(callback.message, catalog)


@router.callback_query(F.data.startswith("menu:"))
async def menu_back_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    target_message_id = int(callback.data.rsplit(":", 1)[1])
    await _show_categories(callback, catalog, target_message_id=target_message_id)


@router.callback_query(F.data.startswith("category:"))
async def category_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    await _show_category_drinks(callback, catalog, callback.data)


@router.callback_query(F.data.startswith("card_back:"))
async def card_back_to_category_handler(
    callback: CallbackQuery,
    catalog: Catalog,
    settings: Settings,
) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    if callback.message is None:
        return
    category_id = callback.data.removeprefix("card_back:")
    await _send_category_drinks_message(callback.message, catalog, category_id)


@router.callback_query(F.data.startswith("back:"))
async def back_to_category_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    payload = callback.data.removeprefix("back:")
    category_id, target_message_id = payload.rsplit(":", 1)
    await _show_category_drinks(
        callback,
        catalog,
        category_id,
        target_message_id=int(target_message_id),
    )


@router.callback_query(F.data.startswith("drink:"))
async def drink_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    drink = catalog.drinks_by_id.get(callback.data)
    if drink is None or callback.message is None:
        return
    await _send_drink_details(callback.message, drink)


async def _prepare_catalog(settings: Settings) -> Catalog:
    catalog = load_catalog(settings)
    if settings.auto_upload_to_cloudinary and settings.cloudinary_configured:
        await sync_catalog_images(settings, catalog)
        catalog = load_catalog(settings)
    return catalog


async def main() -> None:
    settings = load_settings()
    if not settings.workbook_path.exists():
        raise RuntimeError(f"Workbook not found: {settings.workbook_path}")
    if not settings.admins_configured:
        raise RuntimeError(
            "ADMIN_USER_IDS is not set. Add one or more Telegram user IDs to .env."
        )

    catalog = await _prepare_catalog(settings)
    bot = Bot(
        token=settings.bot_token or "",
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot, catalog=catalog, settings=settings)


if __name__ == "__main__":
    asyncio.run(main())
