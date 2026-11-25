from datetime import datetime
from uuid import UUID

from app.features.assistant.domain import (
    ConversationState,
    ConversationTurn,
    CustomerPreference,
    PresentedProductReference,
)


def active_requirements(
    preferences: list[CustomerPreference],
) -> list[CustomerPreference]:
    """Beliefs and replaced history never become retrieval constraints."""
    return [
        preference
        for preference in preferences
        if preference.status == "active" and preference.nature == "requirement"
    ]


def replace_same_slot_preferences(
    existing: list[CustomerPreference],
    new: list[CustomerPreference],
) -> list[CustomerPreference]:
    """Replace only matching active requirements; retain all other preference history."""
    replaced_identities = {
        _logical_slot(preference)
        for preference in new
        if preference.status == "active" and preference.nature == "requirement"
    }
    retained = [
        (
            preference.model_copy(update={"status": "replaced"})
            if preference.status == "active"
            and preference.nature == "requirement"
            and _logical_slot(preference) in replaced_identities
            else preference
        )
        for preference in existing
    ]
    return [*retained, *new]


def _logical_slot(preference: CustomerPreference) -> tuple[str, str | None]:
    key = preference.key if preference.slot == "characteristic" else None
    return preference.slot, key


def append_interaction(
    state: ConversationState,
    *,
    customer_turn: ConversationTurn,
    assistant_turn: ConversationTurn,
    new_preferences: list[CustomerPreference],
    presentations: list[PresentedProductReference],
) -> ConversationState:
    """Validate the resulting browser-held state; the server never persists it."""
    return ConversationState.model_validate(
        {
            **state.model_dump(),
            "turns": [*state.turns, customer_turn, assistant_turn],
            "preferences": replace_same_slot_preferences(
                state.preferences, new_preferences
            ),
            "presentedProducts": presentations,
        }
    )


def assign_presented_references(
    existing: list[PresentedProductReference],
    product_ids: list[str],
    *,
    assistant_turn_id: UUID,
) -> list[PresentedProductReference]:
    references = list(existing)
    by_product = {reference.productId: reference for reference in references}
    next_ordinal = max((reference.ordinal for reference in references), default=0) + 1
    for product_id in product_ids:
        if product_id in by_product:
            continue
        reference = PresentedProductReference(
            ordinal=next_ordinal,
            productId=product_id,
            firstPresentedTurnId=assistant_turn_id,
        )
        references.append(reference)
        by_product[product_id] = reference
        next_ordinal += 1
    return references


def resolve_presented_reference(
    references: list[PresentedProductReference],
    ordinal: int,
) -> PresentedProductReference | None:
    """Resolve by stable ordinal, never by the latest retrieval ranking."""
    return next((reference for reference in references if reference.ordinal == ordinal), None)


def new_customer_turn(text: str, *, turn_id: UUID, created_at: datetime) -> ConversationTurn:
    return ConversationTurn(turnId=turn_id, role="customer", text=text, createdAt=created_at)


def new_assistant_turn(
    text: str,
    *,
    turn_id: UUID,
    interaction_id: UUID,
    created_at: datetime,
) -> ConversationTurn:
    return ConversationTurn(
        turnId=turn_id,
        role="assistant",
        text=text,
        createdAt=created_at,
        interactionId=interaction_id,
    )
