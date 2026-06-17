from __future__ import annotations

import json
from datetime import datetime, UTC

from app.catalog import export_drink_cards
from app.config import load_settings


def main() -> None:
    settings = load_settings(require_bot_token=False)
    cards = export_drink_cards(settings)
    existing_payload: dict[str, object] = {}
    existing_cards: dict[str, object] = {}
    if settings.drink_cards_path.exists():
        existing_payload = json.loads(settings.drink_cards_path.read_text(encoding="utf-8"))
        raw_existing_cards = existing_payload.get("drinks", {})
        if isinstance(raw_existing_cards, dict):
            existing_cards = raw_existing_cards

    for key, card in existing_cards.items():
        if not isinstance(card, dict):
            continue
        if key not in cards:
            cards[key] = card
            continue

        merged_card = dict(cards[key])
        for field in (
            "source_name",
            "name",
            "category_name",
            "volume",
            "recipe",
            "method",
            "serving",
        ):
            if field in card:
                merged_card[field] = card[field]
        cards[key] = merged_card

    payload = {
        "version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source_workbook": settings.workbook_path.name,
        "drinks": cards,
    }

    settings.drink_cards_path.parent.mkdir(parents=True, exist_ok=True)
    settings.drink_cards_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {len(cards)} drink cards to {settings.drink_cards_path}")


if __name__ == "__main__":
    main()
