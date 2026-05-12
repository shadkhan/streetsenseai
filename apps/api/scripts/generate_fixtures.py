"""SM-008 — CLI tool to generate synthetic Street Manager fixture data.

Usage:
    uv run python -m scripts.generate_fixtures \\
        --count 5000 \\
        --start 2026-01-01 \\
        --end 2026-12-31 \\
        --output apps/api/tests/fixtures/works_2026.json \\
        --seed 42 \\
        --include-edge-cases overrun,modified,cancelled \\
        --critical-corridors "A38 Birmingham,M42 Jn 3-4,A1 Leeds North"

See ADR-022 for the rationale behind generating synthetic data before
connecting to the live Street Manager API.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="generate_fixtures",
        description="Generate synthetic Street Manager permit fixtures (SM-008).",
    )
    parser.add_argument("--count", type=int, default=1000, help="Number of permits to generate")
    parser.add_argument("--start", type=str, default="2026-01-01", help="Window start (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2026-12-31", help="Window end (YYYY-MM-DD)")
    parser.add_argument(
        "--output",
        type=str,
        default="tests/fixtures/works_2026.json",
        help="Output JSON file path",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for determinism")
    parser.add_argument(
        "--include-edge-cases",
        type=str,
        default="",
        help="Comma-separated edge case types: overrun,modified,cancelled,weekend_only,school_term_peak",
    )
    parser.add_argument(
        "--critical-corridors",
        type=str,
        default="",
        help="Comma-separated corridor names for concurrent-works clusters",
    )
    parser.add_argument(
        "--corridor-cluster-size",
        type=int,
        default=15,
        help="Number of permits per corridor cluster (default: 15)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    # Import here so the module is importable without side-effects
    from services.synthetic.generator import SyntheticStreetManagerGenerator

    args = _parse_args(argv)

    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)
    edge_cases = [e.strip() for e in args.include_edge_cases.split(",") if e.strip()]
    corridors = [c.strip() for c in args.critical_corridors.split(",") if c.strip()]

    gen = SyntheticStreetManagerGenerator(seed=args.seed)

    print(f"Generating {args.count} permits ({args.start} to {args.end}, seed={args.seed})...")

    # Base generation
    works = gen.generate(args.count, start_date, end_date)

    # Corridor clusters (appended to works list)
    cluster_count = 0
    for corridor in corridors:
        cluster = gen.generate_corridor_cluster(
            corridor,
            count=args.corridor_cluster_size,
            date_window=(start_date, end_date),
        )
        works.extend(cluster)
        cluster_count += len(cluster)
        print(f"  + {len(cluster)} permits for corridor '{corridor}'")

    # Edge case injection
    if edge_cases:
        works = gen.inject_edge_cases(works, edge_cases)
        print(f"  Edge cases injected: {edge_cases}")

    total = len(works)

    # Serialise
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [w.model_dump(by_alias=True, mode="json") for w in works]
    output_path.write_text(json.dumps(payload, indent=2))

    # Summary report
    statuses = Counter(w.status.value for w in works)
    authorities = Counter(w.authority for w in works)
    promoters = Counter(w.promoter for w in works)
    geo_types = Counter(w.geometry.type for w in works)

    print(f"\n{'-' * 60}")
    print("  SYNTHETIC FIXTURE SUMMARY")
    print(f"{'-' * 60}")
    print(f"  Total permits       : {total:,}")
    print(f"  Base permits        : {args.count:,}")
    print(f"  Corridor clusters   : {cluster_count:,} across {len(corridors)} corridor(s)")
    print(f"  Edge cases injected : {edge_cases or 'none'}")
    print(f"  Output              : {output_path}")
    print(f"  File size           : {output_path.stat().st_size / 1024:.1f} KB")
    print("\n  By status:")
    for status, count in sorted(statuses.items(), key=lambda x: -x[1]):
        print(f"    {status:<35} {count:>5}  ({count/total*100:.1f}%)")
    print("\n  By authority (top 5):")
    for auth, count in authorities.most_common(5):
        print(f"    {auth:<40} {count:>5}")
    print("\n  By promoter (top 5):")
    for promoter, count in promoters.most_common(5):
        print(f"    {promoter:<40} {count:>5}")
    print("\n  Geometry types:")
    for geo_type, count in geo_types.items():
        print(f"    {geo_type:<20} {count:>5}  ({count/total*100:.1f}%)")
    print(f"{'-' * 60}\n")


if __name__ == "__main__":
    main(sys.argv[1:])
