import argparse
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

import psycopg
from pydantic import Field, model_validator

from app.core.config import get_settings
from app.core.validation import NonEmptyString, Product, StrictSchema
from app.features.assistant.domain import (
    AssistantInteractionRequest,
    AssistantInteractionResponse,
    ConversationState,
)
from app.features.assistant.interaction_service import InteractionService
from app.features.catalog.postgres_repository import PostgresCatalogRepository
from app.lib.ai.fake_provider import FakeLanguageModelProvider
from scripts.generate_embeddings import FAKE_MODEL_ID

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = REPOSITORY_ROOT / "data/evaluation"
DATASET_NAMES = ("discovery", "qa", "insufficient-evidence", "refinement")


class DatasetProvenance(StrictSchema):
    sourceType: Literal["synthetic"]
    method: NonEmptyString
    reviewStatus: Literal["draft", "reviewed", "approved"]
    humanLabeling: bool
    contaminationControls: NonEmptyString


class DatasetMetadata(StrictSchema):
    recordType: Literal["metadata"]
    datasetId: str
    datasetVersion: str
    generatedAt: datetime
    caseCount: int = Field(ge=1)
    provenance: DatasetProvenance


class EvaluationCase(StrictSchema):
    recordType: Literal["case"]
    caseId: str
    message: str | None = None
    turns: list[str] | None = None
    expect: dict

    @model_validator(mode="after")
    def require_one_input_shape(self) -> "EvaluationCase":
        if (self.message is None) == (self.turns is None):
            raise ValueError("Each case requires exactly one of message or turns")
        return self


def load_dataset(path: Path) -> tuple[DatasetMetadata, list[EvaluationCase]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not records:
        raise ValueError(f"Dataset is empty: {path}")
    metadata = DatasetMetadata.model_validate(records[0])
    cases = [EvaluationCase.model_validate(record) for record in records[1:]]
    case_ids = [case.caseId for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError(f"Duplicate caseId in {path}")
    if len(cases) != metadata.caseCount:
        raise ValueError(f"caseCount does not match records in {path}")
    return metadata, cases


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def empty_conversation() -> ConversationState:
    return ConversationState(
        conversationId=uuid4(),
        createdAt=datetime.now(UTC),
        turns=[],
        preferences=[],
        presentedProducts=[],
    )


class Evaluator:
    def __init__(self, service: InteractionService, products: list[Product]) -> None:
        self.service = service
        self.products = {product.id: product for product in products}
        self.latencies: list[float] = []
        self.failures: list[dict[str, str]] = []

    def call(self, message: str, conversation: ConversationState | None = None) -> AssistantInteractionResponse:
        request = AssistantInteractionRequest(
            conversation=conversation or empty_conversation(), message=message
        )
        started = time.perf_counter()
        response = self.service.handle(request)
        self.latencies.append((time.perf_counter() - started) * 1000)
        return response

    def valid_presentations(self, response: AssistantInteractionResponse) -> bool:
        return all(
            presentation.product.id in self.products
            and presentation.product == self.products[presentation.product.id]
            for presentation in response.presentations
        )

    def discovery_case(self, case: EvaluationCase) -> tuple[bool, float | None]:
        assert case.message is not None
        response = self.call(case.message)
        expected = case.expect
        relevant = set(expected["relevantProductIds"])
        returned = {presentation.product.id for presentation in response.presentations}
        valid = self.valid_presentations(response) and returned <= relevant
        if expected["replyKind"] == "recommendations":
            success = response.reply.kind == "recommendations" and bool(returned) and valid
        else:
            success = response.reply.kind == "no_match" and not returned
        recall = len(returned & relevant) / len(relevant) if relevant else None
        if not success:
            self.failures.append({"caseId": case.caseId, "reason": response.reply.kind})
        return success, recall

    def qa_case(self, case: EvaluationCase) -> bool:
        assert case.message is not None
        response = self.call(case.message)
        expected = case.expect
        success = (
            response.reply.kind == expected["replyKind"]
            and len(response.presentations) == 1
            and response.presentations[0].product.id == expected["productId"]
            and expected["textContains"].lower() in response.reply.text.lower()
            and any(
                expected["groundingField"] in grounding.fields
                for grounding in response.presentations[0].grounding
            )
            and self.valid_presentations(response)
        )
        if not success:
            self.failures.append({"caseId": case.caseId, "reason": response.reply.text})
        return success

    def insufficient_case(self, case: EvaluationCase) -> bool:
        assert case.message is not None
        response = self.call(case.message)
        expected = case.expect
        success = (
            response.reply.kind == expected["replyKind"]
            and expected["textContains"].lower() in response.reply.text.lower()
            and (expected["allowPresentations"] or not response.presentations)
            and self.valid_presentations(response)
        )
        if not success:
            self.failures.append({"caseId": case.caseId, "reason": response.reply.text})
        return success

    def refinement_case(self, case: EvaluationCase) -> bool:
        assert case.turns is not None
        first = self.call(case.turns[0])
        response = self.call(case.turns[1], first.conversation)
        expected = case.expect
        relevant = set(expected["relevantProductIds"])
        returned = {presentation.product.id for presentation in response.presentations}
        valid = self.valid_presentations(response) and returned <= relevant
        if expected["replyKind"] == "recommendations":
            success = response.reply.kind == "recommendations" and bool(returned) and valid
        else:
            success = response.reply.kind == "no_match" and not returned
        active = [
            preference
            for preference in response.conversation.preferences
            if preference.status == "active" and preference.nature == "requirement"
        ]
        category = next((item for item in active if item.slot == "category"), None)
        budget = next((item for item in active if item.slot == "budget"), None)
        success = success and category is not None and category.value["id"] == expected["categoryId"]
        success = success and budget is not None and budget.value["amountMinor"] == expected["maxPriceMinor"]
        expected_keys = set(expected["attributes"])
        actual_keys = {item.key for item in active if item.slot == "characteristic"}
        success = success and expected_keys <= actual_keys
        if not success:
            self.failures.append({"caseId": case.caseId, "reason": response.reply.kind})
        return success


def rate(successes: list[bool]) -> float:
    return sum(successes) / len(successes) if successes else 0


def run_evaluation(retrieval: str) -> dict:
    datasets = {}
    loaded = {}
    for name in DATASET_NAMES:
        metadata, cases = load_dataset(DATASET_ROOT / f"{name}.jsonl")
        datasets[name] = {"version": metadata.datasetVersion, "cases": len(cases)}
        loaded[name] = cases

    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        repository = PostgresCatalogRepository(connection)
        metadata = repository.get_metadata()
        assert metadata is not None
        provider = FakeLanguageModelProvider()
        service = InteractionService(
            repository=repository,
            provider=provider,
            emit_event=lambda _event: None,
            retrieval=retrieval,
        )
        evaluator = Evaluator(service, repository.list_products())
        discovery_results = [evaluator.discovery_case(case) for case in loaded["discovery"]]
        qa_successes = [evaluator.qa_case(case) for case in loaded["qa"]]
        insufficient_successes = [
            evaluator.insufficient_case(case) for case in loaded["insufficient-evidence"]
        ]
        refinement_successes = [
            evaluator.refinement_case(case) for case in loaded["refinement"]
        ]

    discovery_successes = [
        success
        for case, (success, _recall) in zip(
            loaded["discovery"], discovery_results, strict=True
        )
        if case.expect["replyKind"] == "recommendations"
    ]
    recalls = [recall for _success, recall in discovery_results if recall is not None]
    p50 = percentile(evaluator.latencies, 0.50)
    p95 = percentile(evaluator.latencies, 0.95)
    return {
        "schemaVersion": "1.0.0",
        "generatedAt": datetime.now(UTC).isoformat(),
        "retrieval": retrieval,
        "catalogVersion": metadata.catalogVersion,
        "provider": provider.provider_name,
        "modelId": provider.model_id,
        "promptVersion": provider.prompt_version,
        "embeddingModelId": FAKE_MODEL_ID if retrieval == "hybrid" else None,
        "datasets": datasets,
        "metrics": {
            "SC-001": {
                "successRate": rate(discovery_successes),
                "passed": sum(discovery_successes),
                "total": len(discovery_successes),
                "target": 0.85,
                "gate": "measured-proxy",
            },
            "SC-002": {
                "successRate": rate(qa_successes),
                "passed": sum(qa_successes),
                "total": len(qa_successes),
                "target": 0.90,
                "gate": "measured",
            },
            "SC-003": {
                "successRate": rate(insufficient_successes),
                "passed": sum(insufficient_successes),
                "total": len(insufficient_successes),
                "target": 0.95,
                "gate": "measured",
            },
            "SC-004": {
                "p50Ms": p50,
                "p95Ms": p95,
                "maxMs": max(evaluator.latencies, default=0),
                "requestCount": len(evaluator.latencies),
                "targetP95Ms": 5000,
                "gate": "latency distribution under agreed evaluation workload",
            },
            "SC-005": {
                "recallAt3": sum(recalls) / len(recalls) if recalls else 0,
                "k": 3,
                "target": 0.90,
                "gate": "release gate: Recall@3 >= 90% (approved 2026-11-25)",
            },
            "SC-006": {
                "successRate": rate(refinement_successes),
                "passed": sum(refinement_successes),
                "total": len(refinement_successes),
                "target": 0.90,
                "gate": "release gate: refinement success >= 90% (approved 2026-11-25)",
            },
        },
        "workload": {
            "iterationsPerCase": 1,
            "concurrency": 1,
            "execution": "in-process InteractionService with PostgreSQL and deterministic fake provider",
            "requestCountIncludesAllRefinementTurns": True,
        },
        "failures": evaluator.failures,
        "limitations": [
            "SC-001 is a catalog-grounded constraint-satisfaction proxy, not human relevance judging.",
            "SC-005 and SC-006 thresholds (>= 90%) were approved 2026-11-25; datasets remain synthetic draft fixtures.",
            "Datasets are synthetic draft fixtures; no human labeling or approval is claimed.",
            "Fake deterministic embeddings exercise pgvector mechanics, not hosted semantic quality.",
        ],
    }


def percentage(value: float) -> str:
    return f"{value * 100:.2f}%"


def write_markdown(report: dict, output: Path) -> None:
    metrics = report["metrics"]
    title = "Lexical baseline evaluation" if report["retrieval"] == "lexical" else "Hybrid candidate evaluation"
    lines = [
        f"# {title}",
        "",
        f"Generated: `{report['generatedAt']}`",
        "",
        "## Reproducibility",
        "",
        f"- Catalog: `{report['catalogVersion']}`",
        f"- Retrieval: `{report['retrieval']}`",
        f"- Provider: `{report['provider']}`",
        f"- Chat model: `{report['modelId']}`",
        f"- Prompt: `{report['promptVersion']}`",
        f"- Embedding model: `{report['embeddingModelId']}`",
    ]
    for name, dataset in report["datasets"].items():
        lines.append(f"- Dataset `{name}`: `{dataset['version']}` ({dataset['cases']} cases)")
    lines.extend(
        [
            "",
            "## Headline metrics",
            "",
            "| Criterion | Result | Gate / target |",
            "|---|---:|---|",
            f"| SC-001 discovery proxy | {percentage(metrics['SC-001']['successRate'])} ({metrics['SC-001']['passed']}/{metrics['SC-001']['total']}) | >= {percentage(metrics['SC-001']['target'])}; measured proxy |",
            f"| SC-002 Q&A correctness | {percentage(metrics['SC-002']['successRate'])} ({metrics['SC-002']['passed']}/{metrics['SC-002']['total']}) | >= {percentage(metrics['SC-002']['target'])} |",
            f"| SC-003 insufficient evidence | {percentage(metrics['SC-003']['successRate'])} ({metrics['SC-003']['passed']}/{metrics['SC-003']['total']}) | >= {percentage(metrics['SC-003']['target'])} |",
            f"| SC-005 Recall@3 | {percentage(metrics['SC-005']['recallAt3'])} | >= {percentage(metrics['SC-005']['target'])} (release gate) |",
            f"| SC-006 refinement | {percentage(metrics['SC-006']['successRate'])} ({metrics['SC-006']['passed']}/{metrics['SC-006']['total']}) | >= {percentage(metrics['SC-006']['target'])} (release gate) |",
            "",
            "## SC-004 — Latency distribution under agreed evaluation workload",
            "",
            f"- Workload: `{json.dumps(report['workload'], sort_keys=True)}`",
            f"- Requests: {metrics['SC-004']['requestCount']}",
            f"- P50: {metrics['SC-004']['p50Ms']:.3f} ms",
            f"- P95: {metrics['SC-004']['p95Ms']:.3f} ms (target <= 5000 ms)",
            f"- Maximum: {metrics['SC-004']['maxMs']:.3f} ms",
            "",
            "## Case failures",
            "",
            f"- {json.dumps(report['failures'])}",
            "",
            "## Limitations and acceptance status",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def gate_failures(metrics: dict) -> list[str]:
    failures: list[str] = []
    for criterion, field, label in (
        ("SC-005", "recallAt3", "Recall@3"),
        ("SC-006", "successRate", "refinement success"),
    ):
        value = float(metrics[criterion][field])
        target = float(metrics[criterion]["target"])
        if value < target:
            failures.append(
                f"{criterion} {label} is {value * 100:.2f}%, "
                f"below the approved target of {target * 100:.0f}%"
            )
    return failures


def write_comparison(baseline: dict, candidate: dict, output: Path) -> None:
    lines = [
        "# Baseline vs hybrid retrieval comparison",
        "",
        "SC-005 (Recall@3) and SC-006 (refinement) are release gates at >= 90%, approved 2026-11-25; deltas below are observations against those targets.",
        "",
        "| Metric | Lexical baseline | Hybrid candidate | Delta |",
        "|---|---:|---:|---:|",
    ]
    for criterion, field in (
        ("SC-001", "successRate"),
        ("SC-002", "successRate"),
        ("SC-003", "successRate"),
        ("SC-005 Recall@3", "recallAt3"),
        ("SC-006", "successRate"),
    ):
        metric_name = criterion.split()[0]
        before = baseline["metrics"][metric_name][field]
        after = candidate["metrics"][metric_name][field]
        lines.append(
            f"| {criterion} | {percentage(before)} | {percentage(after)} | {(after - before) * 100:+.2f} pp |"
        )
    before = baseline["metrics"]["SC-004"]["p95Ms"]
    after = candidate["metrics"]["SC-004"]["p95Ms"]
    lines.append(f"| SC-004 P95 | {before:.3f} ms | {after:.3f} ms | {after - before:+.3f} ms |")
    lines.extend(
        [
            "",
            "Both runs use identical dataset versions and one sequential request per case/turn. Differences are observations, not approved release-gate judgments.",
            "",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval", choices=("lexical", "hybrid"), default="lexical")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metrics-output", type=Path)
    parser.add_argument("--compare-to", type=Path)
    parser.add_argument("--comparison-output", type=Path)
    args = parser.parse_args()

    report = run_evaluation(args.retrieval)
    write_markdown(report, args.output)
    metrics_output = args.metrics_output or args.output.with_suffix(".metrics.json")
    metrics_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.compare_to:
        baseline = json.loads(args.compare_to.read_text(encoding="utf-8"))
        comparison_output = args.comparison_output or args.output.with_name("comparison.md")
        write_comparison(baseline, report, comparison_output)
    print(json.dumps({"output": str(args.output), "metrics": report["metrics"]}, indent=2))
    failures = gate_failures(report["metrics"])
    if failures:
        raise SystemExit("\n".join(f"RELEASE GATE FAILED: {failure}" for failure in failures))


if __name__ == "__main__":
    main()
