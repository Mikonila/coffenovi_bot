from __future__ import annotations

import asyncio

from app.catalog import load_catalog
from app.cloudinary import sync_catalog_images
from app.config import load_settings


async def main() -> None:
    settings = load_settings(require_bot_token=False)
    if not settings.workbook_path.exists():
        raise RuntimeError(f"Workbook not found: {settings.workbook_path}")

    catalog = load_catalog(settings)
    uploaded = await sync_catalog_images(settings, catalog)
    print(f"Uploaded or reused {len(uploaded)} Cloudinary assets.")
    print(f"Cache updated: {settings.cloudinary_cache_path}")


if __name__ == "__main__":
    asyncio.run(main())
