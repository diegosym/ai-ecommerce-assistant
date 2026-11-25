import re
from decimal import Decimal

from app.core.validation import Product
from app.features.assistant.domain import RankedCandidate
from app.lib.ai.prompts.boundaries import is_out_of_scope
from app.lib.ai.provider import (
    ExtractedPreference,
    PreferenceExtraction,
    QuestionExtraction,
    ResponseSelection,
)

CATEGORY_ALIASES = {
    "headphone": "headphones",
    "headphones": "headphones",
    "earbud": "headphones",
    "earbuds": "headphones",
    "laptop": "laptops",
    "laptops": "laptops",
    "smartwatch": "smartwatches",
    "smartwatches": "smartwatches",
    "watch": "smartwatches",
    "watches": "smartwatches",
    "camera": "cameras",
    "cameras": "cameras",
    "speaker": "speakers",
    "speakers": "speakers",
}


class FakeLanguageModelProvider:
    """Deterministic, credential-free preference extraction for local development."""

    provider_name = "fake"
    model_id = "fake-chat-v1"
    prompt_version = "fake-discovery-v1"

    def extract_preferences(self, *, message: str) -> PreferenceExtraction:
        text = message.lower()
        if is_out_of_scope(text):
            return PreferenceExtraction(intent="out_of_scope")
        question = self._extract_question(text)
        if question is not None:
            return PreferenceExtraction(
                intent="product_question",
                question=question,
                beliefs=self._extract_beliefs(text),
            )
        preferences: list[ExtractedPreference] = []

        category = next(
            (category_id for alias, category_id in CATEGORY_ALIASES.items() if re.search(rf"\b{alias}\b", text)),
            None,
        )
        if category is not None:
            preferences.append(
                ExtractedPreference(slot="category", value={"id": category})
            )

        budget = self._extract_budget(text)
        if budget is not None:
            preferences.append(ExtractedPreference(slot="budget", value=budget))

        connectivity = self._extract_connectivity(text)
        if connectivity is not None:
            preferences.append(self._characteristic("connectivity", connectivity))

        if re.search(r"noise[\s-]*(?:cancellation|cancelling)|\banc\b", text):
            preferences.append(self._characteristic("noise-cancellation", True))

        for phrase, key in (
            ("water resistant", "water-resistant"),
            ("water-resistant", "water-resistant"),
            ("waterproof", "waterproof"),
            ("touchscreen", "touchscreen"),
            ("touch screen", "touchscreen"),
        ):
            if phrase in text:
                preferences.append(self._characteristic(key, True))
                break

        if re.search(r"\b4k\b", text):
            preferences.append(self._characteristic("video-4k", True))

        battery_match = re.search(r"(?:at least|minimum of|min)\s*(\d+)\s*hours?", text)
        if battery_match is not None:
            preferences.append(
                ExtractedPreference(
                    slot="characteristic",
                    key="battery-life",
                    value={
                        "key": "battery-life",
                        "operator": "min",
                        "value": int(battery_match.group(1)),
                    },
                )
            )

        assumptions = []
        if category is not None and budget is None:
            assumptions.append("No budget was stated, so matching products are shown at any price.")
        return PreferenceExtraction(preferences=preferences, assumptions=assumptions)

    def select_response(
        self,
        *,
        message: str,
        candidates: list[RankedCandidate],
        products: list[Product],
    ) -> ResponseSelection:
        del message, products
        return ResponseSelection(productIds=[candidate.productId for candidate in candidates[:3]])

    @staticmethod
    def _extract_question(text: str) -> QuestionExtraction | None:
        attributes = (
            (("price", "cost", "how much"), "price"),
            (("battery",), "battery-life"),
            (("noise cancellation", "noise-cancellation", "noise cancelling"), "noise-cancellation"),
            (("weight", "lighter", "lightest"), "weight"),
            (("warranty",), "warranty"),
            (("bluetooth", "wi-fi", "wifi", "connectivity"), "connectivity"),
            (("waterproof",), "waterproof"),
            (("water resistant", "water-resistant"), "water-resistant"),
            (("touchscreen", "touch screen"), "touchscreen"),
            (("4k",), "video-4k"),
        )
        attribute = next(
            (key for phrases, key in attributes if any(phrase in text for phrase in phrases)),
            None,
        )
        looks_like_question = "?" in text or bool(
            re.match(r"^(?:what|which|does|do|is|are|can|could|how|i thought)\b", text)
        )
        if attribute is None or not looks_like_question:
            return None
        ordinals = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3}
        ordinal = next(
            (value for word, value in ordinals.items() if re.search(rf"\b{word}\b", text)),
            None,
        )
        explicit_product = re.search(r"\bproduct\s+([a-z0-9]+(?:-[a-z0-9]+)+)\b", text)
        catalog_id = re.search(r"\b([a-z]+-\d{3})\b", text)
        product_id = (
            explicit_product.group(1)
            if explicit_product is not None
            else catalog_id.group(1)
            if catalog_id is not None
            else None
        )
        return QuestionExtraction(
            attribute=attribute,
            ordinal=ordinal,
            productId=product_id,
            comparative="which" in text and ("lighter" in text or "lightest" in text),
        )

    @staticmethod
    def _extract_beliefs(text: str) -> list[ExtractedPreference]:
        if not re.search(r"\b(?:thought|believe|think)\b", text):
            return []
        match = re.search(r"\$\s*(\d+(?:\.\d{1,2})?)", text)
        if match is None:
            return []
        return [
            ExtractedPreference(
                slot="budget",
                value={
                    "amountMinor": int(Decimal(match.group(1)) * 100),
                    "currency": "USD",
                },
            )
        ]

    @staticmethod
    def _extract_budget(text: str) -> dict[str, int | str] | None:
        match = re.search(
            r"(?:budget\s*(?:of|is|:)?|under|less than|up to|max(?:imum)?|for)\s*"
            r"\$?\s*(\d+(?:\.\d{1,2})?)",
            text,
        )
        if match is None:
            return None
        amount_minor = int(Decimal(match.group(1)) * 100)
        return {"amountMinor": amount_minor, "currency": "USD"}

    @staticmethod
    def _extract_connectivity(text: str) -> str | None:
        if "bluetooth" in text:
            return "bluetooth"
        if "wi-fi" in text or "wifi" in text:
            return "wi-fi"
        if "wireless" in text:
            return "wireless"
        return None

    @staticmethod
    def _characteristic(key: str, value: str | bool) -> ExtractedPreference:
        return ExtractedPreference(
            slot="characteristic",
            key=key,
            value={"key": key, "operator": "equals", "value": value},
        )
