from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import re


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    project_dir: Path
    bot_token: str | None
    admin_user_ids: frozenset[int]
    editor_user_ids: frozenset[int]
    extra_access_user_ids: frozenset[int]
    workbook_path: Path
    drink_cards_path: Path
    assets_dir: Path
    cloudinary_cache_path: Path
    cloudinary_cloud_name: str | None
    cloudinary_api_key: str | None
    cloudinary_api_secret: str | None
    cloudinary_folder: str
    auto_upload_to_cloudinary: bool

    @property
    def cloudinary_configured(self) -> bool:
        return all(
            [
                self.cloudinary_cloud_name,
                self.cloudinary_api_key,
                self.cloudinary_api_secret,
            ]
        )

    @property
    def admins_configured(self) -> bool:
        return bool(self.admin_user_ids)

    @property
    def access_user_ids(self) -> frozenset[int]:
        return self.admin_user_ids | self.editor_user_ids | self.extra_access_user_ids

    @property
    def access_configured(self) -> bool:
        return bool(self.access_user_ids)


def _parse_admin_user_ids(raw_value: str | None) -> frozenset[int]:
    if not raw_value:
        return frozenset()

    parts = [part.strip() for part in re.split(r"[\s,;]+", raw_value) if part.strip()]
    admin_ids: set[int] = set()
    for part in parts:
        try:
            admin_ids.add(int(part))
        except ValueError as exc:
            raise RuntimeError(
                f"ADMIN_USER_IDS contains invalid Telegram user id: {part!r}"
            ) from exc
    return frozenset(admin_ids)


def load_settings(*, require_bot_token: bool = True) -> Settings:
    project_dir = Path(__file__).resolve().parent.parent
    _load_env_file(project_dir / ".env")

    bot_token = os.getenv("BOT_TOKEN")
    if require_bot_token and not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Fill it in .env or environment.")

    workbook_path = Path(
        os.getenv("WORKBOOK_PATH", str(project_dir / "HercegNovi Standards.xlsx"))
    ).expanduser()
    if not workbook_path.is_absolute():
        workbook_path = (project_dir / workbook_path).resolve()

    drink_cards_path = Path(
        os.getenv("DRINK_CARDS_PATH", str(project_dir / "data" / "drink_cards.json"))
    )
    if not drink_cards_path.is_absolute():
        drink_cards_path = (project_dir / drink_cards_path).resolve()

    assets_dir = Path(os.getenv("ASSETS_DIR", str(project_dir / "assets" / "images")))
    if not assets_dir.is_absolute():
        assets_dir = (project_dir / assets_dir).resolve()

    cache_path = Path(
        os.getenv("CLOUDINARY_CACHE_PATH", str(project_dir / "data" / "cloudinary_urls.json"))
    )
    if not cache_path.is_absolute():
        cache_path = (project_dir / cache_path).resolve()

    return Settings(
        project_dir=project_dir,
        bot_token=bot_token,
        admin_user_ids=_parse_admin_user_ids(os.getenv("ADMIN_USER_IDS")),
        editor_user_ids=_parse_admin_user_ids(
            os.getenv("EDITOR_USER_IDS", "816471270,1339362869")
        ),
        extra_access_user_ids=_parse_admin_user_ids(
            os.getenv("ACCESS_USER_IDS", "5249955166")
        ),
        workbook_path=workbook_path,
        drink_cards_path=drink_cards_path,
        assets_dir=assets_dir,
        cloudinary_cache_path=cache_path,
        cloudinary_cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        cloudinary_api_key=os.getenv("CLOUDINARY_API_KEY"),
        cloudinary_api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        cloudinary_folder=os.getenv("CLOUDINARY_FOLDER", "coffee-novi-bot"),
        auto_upload_to_cloudinary=_bool_env("AUTO_UPLOAD_TO_CLOUDINARY", default=False),
    )
