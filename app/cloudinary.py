from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path

import aiohttp

from app.catalog import Catalog
from app.config import Settings

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_connect=10, sock_read=20)


def _signature(params: dict[str, str], api_secret: str) -> str:
    payload = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha1(f"{payload}{api_secret}".encode("utf-8")).hexdigest()


def _load_cache(cache_path: Path) -> dict[str, str]:
    if not cache_path.exists():
        return {}
    return json.loads(cache_path.read_text(encoding="utf-8"))


def _save_cache(cache_path: Path, cache: dict[str, str]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _upload_endpoint(settings: Settings, resource_type: str) -> str:
    return f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/{resource_type}/upload"


def _destroy_endpoint(settings: Settings, resource_type: str) -> str:
    return f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/{resource_type}/destroy"


def _drink_cards_remote_url(settings: Settings) -> str:
    return (
        f"https://res.cloudinary.com/{settings.cloudinary_cloud_name}/raw/upload/"
        f"{settings.cloudinary_folder}/drink_cards.json"
    )


async def _upload_bytes(
    settings: Settings,
    *,
    resource_type: str,
    public_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> dict[str, object]:
    if not settings.cloudinary_configured:
        raise RuntimeError(
            "Cloudinary credentials are incomplete. "
            "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET."
        )

    timestamp = str(int(time.time()))
    signature_params = {
        "folder": settings.cloudinary_folder,
        "invalidate": "true",
        "overwrite": "true",
        "public_id": public_id,
        "timestamp": timestamp,
    }

    form = aiohttp.FormData()
    form.add_field("api_key", settings.cloudinary_api_key or "")
    form.add_field("timestamp", timestamp)
    form.add_field("folder", settings.cloudinary_folder)
    form.add_field("public_id", public_id)
    form.add_field("overwrite", "true")
    form.add_field("invalidate", "true")
    form.add_field(
        "signature",
        _signature(signature_params, settings.cloudinary_api_secret or ""),
    )
    form.add_field(
        "file",
        file_bytes,
        filename=filename,
        content_type=content_type,
    )

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.post(_upload_endpoint(settings, resource_type), data=form) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(f"Cloudinary upload failed for {public_id}: {payload}")
                return payload
    except asyncio.TimeoutError as exc:
        raise RuntimeError(f"Cloudinary upload timed out for {public_id}.") from exc
    except aiohttp.ClientError as exc:
        raise RuntimeError(f"Cloudinary upload failed for {public_id}: {exc}") from exc


async def upload_editor_image(
    settings: Settings,
    *,
    file_bytes: bytes,
    filename: str,
    public_id: str,
) -> tuple[str, str]:
    payload = await _upload_bytes(
        settings,
        resource_type="image",
        public_id=public_id,
        file_bytes=file_bytes,
        filename=filename,
        content_type="image/jpeg",
    )
    secure_url = str(payload.get("secure_url", "")).strip()
    returned_public_id = str(payload.get("public_id", public_id)).strip()
    if not secure_url:
        raise RuntimeError(f"Cloudinary image upload returned no secure_url: {payload}")
    return returned_public_id, secure_url


async def delete_editor_image(settings: Settings, public_id: str) -> None:
    if not public_id or not settings.cloudinary_configured:
        return

    timestamp = str(int(time.time()))
    signature_params = {
        "invalidate": "true",
        "public_id": public_id,
        "timestamp": timestamp,
    }
    form = aiohttp.FormData()
    form.add_field("api_key", settings.cloudinary_api_key or "")
    form.add_field("timestamp", timestamp)
    form.add_field("public_id", public_id)
    form.add_field("invalidate", "true")
    form.add_field(
        "signature",
        _signature(signature_params, settings.cloudinary_api_secret or ""),
    )

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.post(_destroy_endpoint(settings, "image"), data=form) as response:
                if response.status >= 400:
                    payload = await response.text()
                    raise RuntimeError(f"Cloudinary delete failed for {public_id}: {payload}")
    except asyncio.TimeoutError as exc:
        raise RuntimeError(f"Cloudinary delete timed out for {public_id}.") from exc
    except aiohttp.ClientError as exc:
        raise RuntimeError(f"Cloudinary delete failed for {public_id}: {exc}") from exc


async def upload_drink_cards_backup(settings: Settings) -> None:
    if not settings.drink_cards_path.exists():
        return

    await _upload_bytes(
        settings,
        resource_type="raw",
        public_id="drink_cards.json",
        file_bytes=settings.drink_cards_path.read_bytes(),
        filename="drink_cards.json",
        content_type="application/json",
    )


async def download_drink_cards_backup(settings: Settings) -> bool:
    if not settings.cloudinary_configured:
        return False

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(_drink_cards_remote_url(settings)) as response:
                if response.status == 404:
                    return False
                if response.status >= 400:
                    raise RuntimeError(
                        f"Cloudinary drink cards download failed: {response.status}"
                    )
                payload = await response.read()
    except asyncio.TimeoutError as exc:
        raise RuntimeError("Cloudinary drink cards download timed out.") from exc
    except aiohttp.ClientError as exc:
        raise RuntimeError(f"Cloudinary drink cards download failed: {exc}") from exc

    settings.drink_cards_path.parent.mkdir(parents=True, exist_ok=True)
    settings.drink_cards_path.write_bytes(payload)
    return True


async def sync_catalog_images(settings: Settings, catalog: Catalog) -> dict[str, str]:
    if not settings.cloudinary_configured:
        raise RuntimeError(
            "Cloudinary credentials are incomplete. "
            "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET."
        )

    cache = _load_cache(settings.cloudinary_cache_path)
    for image_id, image_path in catalog.image_registry.items():
        if image_id in cache:
            continue

        payload = await _upload_bytes(
            settings,
            resource_type="image",
            public_id=Path(image_id).stem,
            file_bytes=image_path.read_bytes(),
            filename=image_path.name,
            content_type="image/jpeg",
        )
        secure_url = str(payload.get("secure_url", "")).strip()
        if not secure_url:
            raise RuntimeError(
                f"Cloudinary response has no secure_url for {image_id}: {payload}"
            )
        cache[image_id] = secure_url

    _save_cache(settings.cloudinary_cache_path, cache)
    return cache
