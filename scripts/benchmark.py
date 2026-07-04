"""Benchmark runner со scoring против ground-truth.

Использование:
    python scripts/benchmark.py            # запуск + печать таблицы
    python scripts/benchmark.py --min-accuracy 0.75   # exit 1 если ниже

Что считаем:
    accuracy = % сценариев, где все 4 условия выполнены:
       - status == expected_status
       - n_items в диапазоне [expected_min_items, expected_max_items]
       - savings_pct в диапазоне [expected_min_savings_pct, expected_max_savings_pct]
       - top1.score >= confidence_min
    MAE по savings_pct
    p50/p95 длительности
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from snabagent.agents import run_lot
from snabagent.db.models import Base
from snabagent.db.repositories import CustomerRepo, LotRepo
from snabagent.db.seed import seed_all
from snabagent.db.session import AsyncSessionLocal, engine
from snabagent.vector.nsi_index import reindex_nsi
from snabagent.vector.supplier_index import reindex_suppliers

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


@dataclass
class ScenarioResult:
    scenario_id: int
    name: str
    status: str
    n_items: int | None
    savings_pct: float | None
    top1_score: float | None
    duration_s: float
    passed: bool
    failure_reasons: list[str]


async def _ensure_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_all()
    await reindex_nsi()
    await reindex_suppliers()


async def _run_one(name: str, raw: str) -> tuple[dict, float]:
    async with AsyncSessionLocal() as s:
        customer = await CustomerRepo(s).get_or_create("SIBUR Demo")
        lot = await LotRepo(s).create(
            {"customer_id": customer.id, "raw_request": raw, "phase": "pre_nmck"}
        )
    state = {
        "lot_id": str(lot.id),
        "customer_id": str(customer.id),
        "raw_request": raw,
        "phase": "pre_nmck",
        "status": "draft",
    }
    t0 = time.perf_counter()
    result = await run_lot(state)
    return result, time.perf_counter() - t0


def _evaluate(row: dict, result: dict, duration_s: float) -> ScenarioResult:
    name = row["scenario_name"]
    scenario_id = int(row["scenario_id"])
    status = result.get("status", "unknown") if isinstance(result, dict) else "unknown"
    n_items = None
    # В state ключ называется "report" (см. reporter_node), но мог называться
    # "final_report" в более ранних версиях. Поддерживаем оба.
    report = (
        result.get("report") or result.get("final_report")
        if isinstance(result, dict)
        else None
    )
    parsed = result.get("parsed_items") if isinstance(result, dict) else None
    if parsed:
        n_items = len(parsed)
    elif report and isinstance(report, dict):
        n_items = len(report.get("items") or [])
    savings = None
    top1_score = None
    if report and isinstance(report, dict):
        savings = report.get("savings_vs_avg_pct")
        top3 = report.get("top_3") or []
        if top3:
            top1_score = top3[0].get("score")

    reasons: list[str] = []
    expected_status = row["expected_status"]
    if status != expected_status:
        reasons.append(f"status={status} expected={expected_status}")
    if n_items is not None:
        mn = int(row["expected_min_items"])
        mx = int(row["expected_max_items"])
        if n_items < mn or n_items > mx:
            reasons.append(f"n_items={n_items} not in [{mn},{mx}]")
    if savings is not None:
        try:
            smn = float(row["expected_min_savings_pct"])
            smx = float(row["expected_max_savings_pct"])
            if savings < smn or savings > smx:
                reasons.append(f"savings_pct={savings:.2f} not in [{smn},{smx}]")
        except (TypeError, ValueError):
            pass
    if top1_score is not None:
        try:
            cmin = float(row["confidence_min"])
            if top1_score < cmin:
                reasons.append(f"top1_score={top1_score} below {cmin}")
        except (TypeError, ValueError):
            pass

    return ScenarioResult(
        scenario_id=scenario_id,
        name=name,
        status=status,
        n_items=n_items,
        savings_pct=savings,
        top1_score=top1_score,
        duration_s=duration_s,
        passed=len(reasons) == 0,
        failure_reasons=reasons,
    )


async def main(min_accuracy: float, scenarios_filter: list[int] | None = None) -> int:
    await _ensure_db()
    gt_path = DATA / "benchmark_ground_truth.csv"
    if not gt_path.exists():
        print(f"ERROR: ground-truth missing: {gt_path}", file=sys.stderr)
        return 2
    with gt_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if scenarios_filter:
        rows = [r for r in rows if int(r["scenario_id"]) in scenarios_filter]

    results: list[ScenarioResult] = []
    timings: list[float] = []
    skipped: list[str] = []
    for row in rows:
        f_path = DATA / "sample_tz" / row["scenario_file"]
        if not f_path.exists():
            skipped.append(row["scenario_file"])
            continue
        raw = f_path.read_text(encoding="utf-8")
        try:
            result, t = await _run_one(row["scenario_name"], raw)
        except Exception as e:
            results.append(
                ScenarioResult(
                    scenario_id=int(row["scenario_id"]),
                    name=row["scenario_name"],
                    status="exception",
                    n_items=None,
                    savings_pct=None,
                    top1_score=None,
                    duration_s=0,
                    passed=False,
                    failure_reasons=[f"exception: {type(e).__name__}: {e}"],
                )
            )
            continue
        timings.append(t)
        res = _evaluate(row, result, t)
        results.append(res)

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    accuracy = (passed / total) if total else 0.0
    p50 = statistics.median(timings) if timings else 0.0
    p95 = (statistics.quantiles(timings, n=20)[-1] if len(timings) >= 5 else max(timings, default=0.0))
    savings_mae = (
        statistics.mean(
            abs((r.savings_pct or 0) - (
                (float(rows[idx]["expected_min_savings_pct"]) + float(rows[idx]["expected_max_savings_pct"])) / 2
            ))
            for idx, r in enumerate(results)
            if r.savings_pct is not None and idx < len(rows)
        )
        if any(r.savings_pct is not None for r in results)
        else 0.0
    )

    print("=== SnabAgent Benchmark ===")
    print(f"scenarios: {total} (passed={passed}, accuracy={accuracy:.1%})")
    print(f"p50 duration: {p50:.2f}s   p95: {p95:.2f}s")
    print(f"savings MAE vs mid-range: {savings_mae:.2f}%")
    if skipped:
        print(f"skipped (file missing): {skipped}")
    print()
    for r in results:
        flag = "OK" if r.passed else "FAIL"
        print(
            f"  [{flag}] {r.scenario_id:>2} {r.name:<32} "
            f"status={r.status:<14} items={r.n_items}  savings={r.savings_pct}"
            f"  top1={r.top1_score}  t={r.duration_s:.1f}s"
        )
        for reason in r.failure_reasons:
            print(f"        - {reason}")

    summary = {
        "total": total,
        "passed": passed,
        "accuracy": accuracy,
        "p50_duration_s": p50,
        "p95_duration_s": p95,
        "savings_mae": savings_mae,
        "skipped": skipped,
        "results": [asdict(r) for r in results],
    }
    out_path = DATA / "benchmark_results.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nJSON: {out_path}")

    if min_accuracy and accuracy < min_accuracy:
        print(
            f"\nFAIL: accuracy {accuracy:.1%} < required {min_accuracy:.0%}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-accuracy", type=float, default=0.0,
                        help="Минимальный accuracy [0..1]; >0 — exit 1 при недостаче")
    parser.add_argument("--scenarios", type=str, default="",
                        help="comma-separated scenario_id, например '1,2,3'")
    args = parser.parse_args()
    f = [int(x) for x in args.scenarios.split(",") if x.strip()] if args.scenarios else None
    sys.exit(asyncio.run(main(args.min_accuracy, f)))
