from uuid import uuid4

from app.features.assistant.conversation_state import (
    active_requirements,
    replace_same_slot_preferences,
)
from app.features.assistant.domain import CustomerPreference


def preference(
    *,
    slot: str,
    value: dict,
    key: str | None = None,
    nature: str = "requirement",
    status: str = "active",
    source_turn_id=None,
) -> CustomerPreference:
    return CustomerPreference(
        preferenceId=uuid4(),
        slot=slot,
        key=key,
        nature=nature,
        value=value,
        sourceTurnId=source_turn_id or uuid4(),
        status=status,
    )


def test_same_slot_replacement_marks_old_value_replaced_and_preserves_unrelated_slots() -> None:
    original_turn = uuid4()
    refinement_turn = uuid4()
    category = preference(slot="category", value={"id": "headphones"}, source_turn_id=original_turn)
    old_budget = preference(
        slot="budget",
        value={"amountMinor": 15000, "currency": "USD"},
        source_turn_id=original_turn,
    )
    new_budget = preference(
        slot="budget",
        value={"amountMinor": 12000, "currency": "USD"},
        source_turn_id=refinement_turn,
    )

    merged = replace_same_slot_preferences([category, old_budget], [new_budget])

    assert merged[0] == category
    assert merged[1].preferenceId == old_budget.preferenceId
    assert merged[1].status == "replaced"
    assert merged[1].value["amountMinor"] == 15000
    assert merged[2].preferenceId == new_budget.preferenceId
    assert merged[2].status == "active"
    assert merged[2].sourceTurnId == refinement_turn
    assert active_requirements(merged) == [category, new_budget]


def test_characteristic_replacement_is_scoped_by_logical_key() -> None:
    connectivity = preference(
        slot="characteristic",
        key="connectivity",
        value={"key": "connectivity", "operator": "equals", "value": "wireless"},
    )
    old_noise = preference(
        slot="characteristic",
        key="noise-cancellation",
        value={"key": "noise-cancellation", "operator": "equals", "value": False},
    )
    new_noise = preference(
        slot="characteristic",
        key="noise-cancellation",
        value={"key": "noise-cancellation", "operator": "equals", "value": True},
    )

    merged = replace_same_slot_preferences([connectivity, old_noise], [new_noise])

    assert merged[0] == connectivity
    assert merged[0].status == "active"
    assert merged[1].status == "replaced"
    assert merged[2] == new_noise
    assert active_requirements(merged) == [connectivity, new_noise]


def test_belief_does_not_replace_or_become_an_active_requirement() -> None:
    requirement = preference(
        slot="budget", value={"amountMinor": 15000, "currency": "USD"}
    )
    belief = preference(
        slot="budget",
        value={"amountMinor": 9900, "currency": "USD"},
        nature="belief",
    )

    merged = replace_same_slot_preferences([requirement], [belief])

    assert merged == [requirement, belief]
    assert requirement.status == "active"
    assert active_requirements(merged) == [requirement]
