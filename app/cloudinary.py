from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import aiohttp

from app.catalog import Catalog
from app.config import Settings


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


async def sync_catalog_images(settings: Settings, catalog: Catalog) -> dict[str, str]:
    if not settings.cloudinary_configured:
        raise RuntimeError(
            "Cloudinary credentials are incomplete. "
            "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET."
        )

    cache = _load_cache(settings.cloudinary_cache_path)
    endpoint = (
        f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/image/upload"
    )

    async with aiohttp.ClientSession() as session:
        for image_id, image_path in catalog.image_registry.items():
            if image_id in cache:
                continue

            timestamp = str(int(time.time()))
            public_id = Path(image_id).stem
            signature_params = {
                "folder": settings.cloudinary_folder,
                "public_id": public_id,
                "timestamp": timestamp,
            }

            form = aiohttp.FormData()
            form.add_field("api_key", settings.cloudinary_api_key or "")
            form.add_field("timestamp", timestamp)
            form.add_field("folder", settings.cloudinary_folder)
            form.add_field("public_id", public_id)
            form.add_field(
                "signature",
                _signature(signature_params, settings.cloudinary_api_secret or ""),
            )
            form.add_field(
                "file",
                image_path.read_bytes(),
                filename=image_path.name,
                content_type="image/jpeg",
            )

            async with session.post(endpoint, data=form) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(
                        f"Cloudinary upload failed for {image_id}: {payload}"
                    )
                secure_url = payload.get("secure_url")
                if not secure_url:
                    raise RuntimeError(
                        f"Cloudinary response has no secure_url for {image_id}: {payload}"
                    )
                cache[image_id] = secure_url

    _save_cache(settings.cloudinary_cache_path, cache)
    return cache
