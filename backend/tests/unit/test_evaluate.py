import json
from pathlib import Path

import pytest

from scripts.evaluate import gate_failures, load_dataset, percentile

DATASET_COUNTS = {
    "discovery": 18,
    "qa": 16,
    "insufficient-evidence": 16,
    "refinement": 16,
}


@pytest.mark.parametrize(("name", "count"), DATASET_COUNTS.items())
def test_loads_versioned_datasets_with_synthetic_provenance(name: str, count: int) -> None:
    path = Path(__file__).resolve().parents[3] / "data/evaluation" / f"{name}.jsonl"

    metadata, cases = load_dataset(path)

    assert metadata.datasetId == name
    assert metadata.datasetVersion == "1.0.0"
    assert metadata.provenance.sourceType == "synthetic"
    assert metadata.provenance.humanLabeling is False
    assert metadata.provenance.reviewStatus == "draft"
    assert len(cases) == count
    assert len({case.caseId for case in cases}) == count


def test_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[3] / "data/evaluation/discovery.jsonl"
    records = [json.loads(line) for line in source.read_text().splitlines()[:3]]
    records[2]["caseId"] = records[1]["caseId"]
    path = tmp_path / "duplicates.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records))

    with pytest.raises(ValueError, match="Duplicate caseId"):
        load_dataset(path)


def test_rejects_missing_provenance(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[3] / "data/evaluation/discovery.jsonl"
    records = [json.loads(line) for line in source.read_text().splitlines()[:2]]
    del records[0]["provenance"]
    path = tmp_path / "missing-provenance.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records))

    with pytest.raises(ValueError):
        load_dataset(path)


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([40, 10, 30, 20], 0.50) == 20
    assert percentile([40, 10, 30, 20], 0.95) == 40
    assert percentile([], 0.95) == 0


def test_release_gates_fail_below_approved_targets() -> None:
    metrics = {
        "SC-005": {"recallAt3": 0.899, "target": 0.90},
        "SC-006": {"successRate": 0.899, "target": 0.90},
    }

    failures = gate_failures(metrics)

    assert any("SC-005" in failure for failure in failures)
    assert any("SC-006" in failure for failure in failures)


def test_release_gates_pass_at_approved_targets() -> None:
    metrics = {
        "SC-005": {"recallAt3": 0.90, "target": 0.90},
        "SC-006": {"successRate": 0.90, "target": 0.90},
    }

    assert gate_failures(metrics) == []
