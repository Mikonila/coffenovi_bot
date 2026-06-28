from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from html import escape

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message

from app.catalog import (
    Catalog,
    Category,
    Drink,
    InfoPage,
    InfoSection,
    load_catalog,
    load_drink_cards_payload,
    save_drink_cards_payload,
)
from app.cloudinary import (
    delete_editor_image,
    download_drink_cards_backup,
    sync_catalog_images,
    upload_drink_cards_backup,
    upload_editor_image,
)
from app.config import Settings, load_settings
from app.keyboards import (
    categories_keyboard,
    drink_navigation_keyboard,
    drinks_keyboard,
    info_section_navigation_keyboard,
    info_sections_keyboard,
)

router = Router()


@dataclass(slots=True)
class PendingEditorAction:
    action: str
    drink_id: str


@dataclass(slots=True)
class UserSession:
    screen_message_ids: list[int] = field(default_factory=list)
    prompt_message_ids: list[int] = field(default_factory=list)
    pending_action: PendingEditorAction | None = None


USER_SESSIONS: dict[int, UserSession] = {}


def _session(user_id: int) -> UserSession:
    return USER_SESSIONS.setdefault(user_id, UserSession())


def _is_admin(user_id: int | None, settings: Settings) -> bool:
    return user_id is not None and user_id in settings.admin_user_ids


def _is_editor(user_id: int | None, settings: Settings) -> bool:
    return user_id is not None and user_id in settings.editor_user_ids


def _has_access(user_id: int | None, settings: Settings) -> bool:
    return user_id is not None and user_id in settings.access_user_ids


def _replace_catalog_state(target: Catalog, updated: Catalog) -> None:
    target.categories = updated.categories
    target.drinks_by_id = updated.drinks_by_id
    target.image_registry = updated.image_registry
    target.info_pages = updated.info_pages


def _reload_catalog(catalog: Catalog, settings: Settings) -> None:
    _replace_catalog_state(catalog, load_catalog(settings))


async def _deny_message(message: Message) -> None:
    await message.answer("У вас нет доступа к этому боту.")


async def _deny_callback(callback: CallbackQuery) -> None:
    await callback.answer("У вас нет доступа к этому боту.", show_alert=True)


def _format_drink_message(drink: Drink) -> str:
    if drink.custom_text:
        return escape(drink.custom_text)

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


def _info_page_by_id(catalog: Catalog, page_id: str) -> InfoPage | None:
    return catalog.info_pages.get(page_id)


def _info_section_by_id(page: InfoPage, section_id: str) -> InfoSection | None:
    return next((section for section in page.sections if section.id == section_id), None)


def _format_info_page_message(page: InfoPage) -> str:
    return f"<b>{escape(page.title)}</b>\nВыберите раздел:"


def _format_info_section_message(page: InfoPage, section: InfoSection) -> str:
    return f"<b>{escape(page.title)}</b>\n<b>{escape(section.title)}</b>\n\n{escape(section.body)}"


async def _delete_messages(bot: Bot, chat_id: int, message_ids: list[int]) -> None:
    for message_id in sorted(set(message_ids), reverse=True):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramBadRequest:
            continue


async def _clear_prompt_messages(bot: Bot, chat_id: int, session: UserSession) -> None:
    if not session.prompt_message_ids:
        return
    await _delete_messages(bot, chat_id, session.prompt_message_ids)
    session.prompt_message_ids.clear()
    session.pending_action = None


async def _clear_screen(bot: Bot, chat_id: int, session: UserSession) -> None:
    if session.screen_message_ids:
        await _delete_messages(bot, chat_id, session.screen_message_ids)
        session.screen_message_ids.clear()


async def _replace_text_screen(
    bot: Bot,
    *,
    chat_id: int,
    user_id: int,
    text: str,
    reply_markup,
) -> None:
    session = _session(user_id)
    await _clear_prompt_messages(bot, chat_id, session)
    await _clear_screen(bot, chat_id, session)
    sent = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    session.screen_message_ids = [sent.message_id]


async def _show_categories_screen(bot: Bot, *, chat_id: int, user_id: int, catalog: Catalog) -> None:
    await _replace_text_screen(
        bot,
        chat_id=chat_id,
        user_id=user_id,
        text="Выберите раздел с напитками:",
        reply_markup=categories_keyboard(catalog.categories),
    )


async def _show_category_drinks_screen(
    bot: Bot,
    *,
    chat_id: int,
    user_id: int,
    catalog: Catalog,
    category_id: str,
) -> None:
    category = _category_by_id(catalog, category_id)
    if category is None:
        return
    await _replace_text_screen(
        bot,
        chat_id=chat_id,
        user_id=user_id,
        text=f"Раздел: <b>{escape(category.name)}</b>\nВыберите напиток:",
        reply_markup=drinks_keyboard(category),
    )


async def _show_info_page_screen(
    bot: Bot,
    *,
    chat_id: int,
    user_id: int,
    catalog: Catalog,
    page_id: str,
) -> None:
    page = _info_page_by_id(catalog, page_id)
    if page is None:
        return
    await _replace_text_screen(
        bot,
        chat_id=chat_id,
        user_id=user_id,
        text=_format_info_page_message(page),
        reply_markup=info_sections_keyboard(page),
    )


async def _show_info_section_screen(
    bot: Bot,
    *,
    chat_id: int,
    user_id: int,
    catalog: Catalog,
    page_id: str,
    section_id: str,
) -> None:
    page = _info_page_by_id(catalog, page_id)
    if page is None:
        return
    section = _info_section_by_id(page, section_id)
    if section is None:
        return
    await _replace_text_screen(
        bot,
        chat_id=chat_id,
        user_id=user_id,
        text=_format_info_section_message(page, section),
        reply_markup=info_section_navigation_keyboard(page_id),
    )


async def _show_drink_screen(
    bot: Bot,
    *,
    chat_id: int,
    user_id: int,
    catalog: Catalog,
    settings: Settings,
    drink_id: str,
) -> None:
    drink = catalog.drinks_by_id.get(drink_id)
    if drink is None:
        return

    session = _session(user_id)
    await _clear_prompt_messages(bot, chat_id, session)
    await _clear_screen(bot, chat_id, session)

    screen_message_ids: list[int] = []
    media_items = _resolve_media_items(drink)
    if len(media_items) == 1:
        sent_photo = await bot.send_photo(chat_id=chat_id, photo=media_items[0])
        screen_message_ids.append(sent_photo.message_id)
    elif len(media_items) > 1:
        media_group = [InputMediaPhoto(media=item) for item in media_items]
        sent_group = await bot.send_media_group(chat_id=chat_id, media=media_group)
        screen_message_ids.extend(message.message_id for message in sent_group)

    sent_text = await bot.send_message(
        chat_id=chat_id,
        text=_format_drink_message(drink),
        reply_markup=drink_navigation_keyboard(
            drink.category_id,
            drink_id=drink.id,
            can_edit=_is_editor(user_id, settings),
        ),
    )
    screen_message_ids.append(sent_text.message_id)
    session.screen_message_ids = screen_message_ids


def _ensure_card_entry(payload: dict[str, object], drink: Drink) -> dict[str, object]:
    drinks = payload.setdefault("drinks", {})
    if not isinstance(drinks, dict):
        raise RuntimeError("drink_cards.json has invalid structure.")

    raw_entry = drinks.get(drink.id)
    if isinstance(raw_entry, dict):
        entry = dict(raw_entry)
    else:
        entry = {}

    entry.setdefault("id", drink.id)
    entry.setdefault("row_number", drink.row_number)
    entry.setdefault("source_name", drink.name)
    entry.setdefault("name", drink.name)
    entry.setdefault("category_name", drink.category_name)
    entry.setdefault("volume", drink.volume)
    entry.setdefault("recipe", drink.recipe)
    entry.setdefault("method", drink.method)
    entry.setdefault("serving", drink.serving)
    entry.setdefault("custom_text", drink.custom_text)
    entry.setdefault("image_mode", "default")
    entry.setdefault("image_urls", list(drink.image_urls))
    entry.setdefault("image_public_ids", list(drink.image_public_ids))
    drinks[drink.id] = entry
    return entry


async def _persist_drink_cards(settings: Settings) -> None:
    if settings.cloudinary_configured:
        await upload_drink_cards_backup(settings)


async def _save_custom_text(
    catalog: Catalog,
    settings: Settings,
    *,
    drink_id: str,
    custom_text: str,
) -> None:
    drink = catalog.drinks_by_id.get(drink_id)
    if drink is None:
        return

    payload = load_drink_cards_payload(settings.drink_cards_path)
    entry = _ensure_card_entry(payload, drink)
    entry["custom_text"] = custom_text.strip()
    save_drink_cards_payload(settings.drink_cards_path, payload)
    await _persist_drink_cards(settings)
    _reload_catalog(catalog, settings)


async def _set_drink_image_mode(
    catalog: Catalog,
    settings: Settings,
    *,
    drink_id: str,
    image_mode: str,
    image_urls: list[str],
    image_public_ids: list[str],
) -> None:
    drink = catalog.drinks_by_id.get(drink_id)
    if drink is None:
        return

    payload = load_drink_cards_payload(settings.drink_cards_path)
    entry = _ensure_card_entry(payload, drink)
    entry["image_mode"] = image_mode
    entry["image_urls"] = image_urls
    entry["image_public_ids"] = image_public_ids
    save_drink_cards_payload(settings.drink_cards_path, payload)
    await _persist_drink_cards(settings)
    _reload_catalog(catalog, settings)


async def _download_telegram_file_bytes(bot: Bot, file_id: str) -> bytes:
    file = await bot.get_file(file_id)
    if not file.file_path:
        raise RuntimeError("Telegram returned file without file_path.")
    url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status >= 400:
                raise RuntimeError(f"Failed to download Telegram file: {response.status}")
            return await response.read()


async def _refresh_drink_text_message(
    bot: Bot,
    *,
    chat_id: int,
    message_id: int,
    drink: Drink,
    settings: Settings,
    user_id: int,
) -> None:
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=_format_drink_message(drink),
        reply_markup=drink_navigation_keyboard(
            drink.category_id,
            drink_id=drink.id,
            can_edit=_is_editor(user_id, settings),
        ),
    )


def _drink_by_pending_action(catalog: Catalog, pending: PendingEditorAction | None) -> Drink | None:
    if pending is None:
        return None
    return catalog.drinks_by_id.get(pending.drink_id)


@router.message(CommandStart())
async def start_handler(message: Message, catalog: Catalog, settings: Settings) -> None:
    if not _has_access(message.from_user.id if message.from_user else None, settings):
        await _deny_message(message)
        return
    if not message.from_user:
        return
    await _show_categories_screen(
        message.bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        catalog=catalog,
    )


@router.callback_query(F.data == "menu")
async def menu_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _has_access(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    await _show_categories_screen(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        catalog=catalog,
    )


@router.callback_query(F.data == "card_menu")
async def card_menu_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _has_access(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    await _show_categories_screen(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        catalog=catalog,
    )


@router.callback_query(F.data.startswith("category:"))
async def category_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _has_access(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    await _show_category_drinks_screen(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        catalog=catalog,
        category_id=callback.data,
    )


@router.callback_query(F.data.startswith("card_back:"))
async def card_back_to_category_handler(
    callback: CallbackQuery,
    catalog: Catalog,
    settings: Settings,
) -> None:
    if not _has_access(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    category_id = callback.data.removeprefix("card_back:")
    await _show_category_drinks_screen(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        catalog=catalog,
        category_id=category_id,
    )


@router.callback_query(F.data.startswith("drink:"))
async def drink_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _has_access(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    await _show_drink_screen(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        catalog=catalog,
        settings=settings,
        drink_id=callback.data,
    )


@router.callback_query(F.data.in_({"info:checklists", "info:dailycleaning", "info:deadlines"}))
async def info_page_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _has_access(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    page_id = callback.data.split(":", 1)[1]
    await _show_info_page_screen(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        catalog=catalog,
        page_id=page_id,
    )


@router.callback_query(F.data.startswith("info_section:"))
async def info_section_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _has_access(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    _, page_id, section_id = callback.data.split(":", 2)
    await _show_info_section_screen(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        catalog=catalog,
        page_id=page_id,
        section_id=section_id,
    )


@router.callback_query(F.data.startswith("editor:edit_info:"))
async def editor_edit_info_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _is_editor(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    drink_id = callback.data.removeprefix("editor:edit_info:")
    session = _session(callback.from_user.id)
    await _clear_prompt_messages(callback.bot, callback.message.chat.id, session)
    session.pending_action = PendingEditorAction(action="edit_info", drink_id=drink_id)
    prompt = await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text="Отправьте новый текст карточки одним сообщением. Он полностью заменит текущую информацию.",
    )
    session.prompt_message_ids = [prompt.message_id]


@router.callback_query(F.data.startswith("editor:add_photo:"))
async def editor_add_photo_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _is_editor(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()
    drink_id = callback.data.removeprefix("editor:add_photo:")
    session = _session(callback.from_user.id)
    await _clear_prompt_messages(callback.bot, callback.message.chat.id, session)
    session.pending_action = PendingEditorAction(action="add_photo", drink_id=drink_id)
    prompt = await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text="Отправьте одну фотографию. Она загрузится в Cloudinary и заменит текущее фото карточки.",
    )
    session.prompt_message_ids = [prompt.message_id]


@router.callback_query(F.data.startswith("editor:remove_photo:"))
async def editor_remove_photo_handler(callback: CallbackQuery, catalog: Catalog, settings: Settings) -> None:
    if not _is_editor(callback.from_user.id if callback.from_user else None, settings):
        await _deny_callback(callback)
        return
    await callback.answer()

    drink_id = callback.data.removeprefix("editor:remove_photo:")
    drink = catalog.drinks_by_id.get(drink_id)
    if drink is None:
        return

    for public_id in drink.image_public_ids:
        await delete_editor_image(settings, public_id)

    await _set_drink_image_mode(
        catalog,
        settings,
        drink_id=drink_id,
        image_mode="none",
        image_urls=[],
        image_public_ids=[],
    )
    await _show_drink_screen(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
        catalog=catalog,
        settings=settings,
        drink_id=drink_id,
    )


@router.message(F.photo)
async def editor_photo_message_handler(message: Message, catalog: Catalog, settings: Settings) -> None:
    if not _is_editor(message.from_user.id if message.from_user else None, settings):
        return
    if not message.from_user:
        return

    session = _session(message.from_user.id)
    if session.pending_action is None or session.pending_action.action != "add_photo":
        return

    drink = _drink_by_pending_action(catalog, session.pending_action)
    if drink is None:
        return

    photo = message.photo[-1]
    file_bytes = await _download_telegram_file_bytes(message.bot, photo.file_id)
    public_id = f"{drink.id.replace(':', '_')}_{int(time.time())}"
    uploaded_public_id, uploaded_url = await upload_editor_image(
        settings,
        file_bytes=file_bytes,
        filename=f"{public_id}.jpg",
        public_id=public_id,
    )

    for old_public_id in drink.image_public_ids:
        await delete_editor_image(settings, old_public_id)

    await _set_drink_image_mode(
        catalog,
        settings,
        drink_id=drink.id,
        image_mode="custom",
        image_urls=[uploaded_url],
        image_public_ids=[uploaded_public_id],
    )

    await _clear_prompt_messages(message.bot, message.chat.id, session)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await _show_drink_screen(
        message.bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        catalog=catalog,
        settings=settings,
        drink_id=drink.id,
    )


@router.message(F.text)
async def editor_text_message_handler(message: Message, catalog: Catalog, settings: Settings) -> None:
    if not _is_editor(message.from_user.id if message.from_user else None, settings):
        return
    if not message.from_user:
        return

    session = _session(message.from_user.id)
    if session.pending_action is None or session.pending_action.action != "edit_info":
        return

    drink = _drink_by_pending_action(catalog, session.pending_action)
    if drink is None or not message.text:
        return

    await _save_custom_text(
        catalog,
        settings,
        drink_id=drink.id,
        custom_text=message.text,
    )
    updated_drink = catalog.drinks_by_id.get(drink.id)
    if updated_drink is None:
        return

    if session.screen_message_ids:
        target_message_id = session.screen_message_ids[-1]
        await _refresh_drink_text_message(
            message.bot,
            chat_id=message.chat.id,
            message_id=target_message_id,
            drink=updated_drink,
            settings=settings,
            user_id=message.from_user.id,
        )

    await _clear_prompt_messages(message.bot, message.chat.id, session)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def _prepare_catalog(settings: Settings) -> Catalog:
    if settings.cloudinary_configured:
        try:
            await download_drink_cards_backup(settings)
        except RuntimeError:
            pass

    catalog = load_catalog(settings)
    if settings.auto_upload_to_cloudinary and settings.cloudinary_configured:
        await sync_catalog_images(settings, catalog)
        catalog = load_catalog(settings)
    return catalog


async def main() -> None:
    settings = load_settings()
    if not settings.workbook_path.exists():
        raise RuntimeError(f"Workbook not found: {settings.workbook_path}")
    if not settings.access_configured:
        raise RuntimeError(
            "No access users configured. Add ADMIN_USER_IDS and/or EDITOR_USER_IDS to .env."
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
