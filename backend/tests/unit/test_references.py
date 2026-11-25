from uuid import uuid4

from app.features.assistant.conversation_state import (
    assign_presented_references,
    resolve_presented_reference,
)
from app.features.assistant.domain import PresentedProductReference


def reference(ordinal: int, product_id: str) -> PresentedProductReference:
    return PresentedProductReference(
        ordinal=ordinal,
        productId=product_id,
        firstPresentedTurnId=uuid4(),
    )


def test_representing_product_keeps_original_ordinal_and_first_presented_turn() -> None:
    original = reference(1, "headphones-002")

    references = assign_presented_references(
        [original], ["headphones-002"], assistant_turn_id=uuid4()
    )

    assert references == [original]
    assert references[0].ordinal == 1
    assert references[0].firstPresentedTurnId == original.firstPresentedTurnId


def test_new_products_append_after_maximum_without_reusing_or_reordering_ordinals() -> None:
    existing = [reference(2, "headphones-002"), reference(5, "headphones-004")]

    references = assign_presented_references(
        existing,
        ["headphones-005", "headphones-002"],
        assistant_turn_id=uuid4(),
    )

    assert [item.ordinal for item in references] == [2, 5, 6]
    assert [item.productId for item in references] == [
        "headphones-002",
        "headphones-004",
        "headphones-005",
    ]
    assert references[:2] == existing


def test_ordinal_resolution_stays_stable_after_later_rank_changes() -> None:
    first = reference(1, "headphones-002")
    second = reference(2, "headphones-004")
    references = assign_presented_references(
        [first, second], ["headphones-006"], assistant_turn_id=uuid4()
    )

    assert resolve_presented_reference(references, 1) == first
    assert resolve_presented_reference(references, 2) == second
    assert resolve_presented_reference(references, 99) is None
