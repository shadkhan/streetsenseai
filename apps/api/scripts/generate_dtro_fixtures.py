"""DT-008 — CLI tool to generate synthetic D-TRO fixture data.

Usage:
    uv run python -m scripts.generate_dtro_fixtures \\
        --output apps/api/tests/fixtures/dtros_2026.json \\
        --seed 42

Generates 500 permanent TROs + 200 TTROs conforming to D-TRO v4.0.0 schema.
See ADR-027 for the three-mode data strategy (synthetic → integration → production).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import uuid
from collections import Counter
from datetime import date
from pathlib import Path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="generate_dtro_fixtures",
        description="Generate synthetic D-TRO fixture data (DT-008, v4.0.0 schema).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tests/fixtures/dtros_2026.json",
        help="Output JSON file path",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for determinism")
    parser.add_argument(
        "--permanent",
        type=int,
        default=500,
        help="Number of permanent TROs to generate",
    )
    parser.add_argument(
        "--temporary",
        type=int,
        default=200,
        help="Number of TTROs to generate",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    from services.synthetic.dtro_generator import (
        _TRO_TYPE_WEIGHTS,
        _build_document,
        _load_authorities,
        _rand_date_past,
        _rand_ttro_dates,
    )

    args = _parse_args(argv)
    rng = random.Random(args.seed)
    authorities = _load_authorities()
    tro_types = [t for t, _ in _TRO_TYPE_WEIGHTS]
    type_weights = [w for _, w in _TRO_TYPE_WEIGHTS]

    records: list[dict] = []
    seq = 0

    for is_temporary, count in [(False, args.permanent), (True, args.temporary)]:
        for _ in range(count):
            seq += 1
            authority = rng.choice(authorities)
            tro_type = rng.choices(tro_types, weights=type_weights)[0]

            if is_temporary:
                valid_from, valid_to = _rand_ttro_dates(rng)
            else:
                valid_from = _rand_date_past(rng, years_back=15)
                valid_to = None

            tro_id = str(uuid.uuid4())
            doc, _, _, _ = _build_document(
                rng, tro_id, authority, tro_type, is_temporary, valid_from, valid_to, seq
            )
            records.append(doc)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2, default=str))

    total = len(records)
    type_counts = Counter(r["body"]["tro"]["type"] for r in records)
    authority_counts = Counter(r["body"]["tro"]["authority"] for r in records)
    temp_count = sum(1 for r in records if r["body"]["tro"]["isTemporary"])

    print(f"\n{'─' * 60}")
    print("  D-TRO FIXTURE SUMMARY (v4.0.0 schema)")
    print(f"{'─' * 60}")
    print(f"  Total orders        : {total}")
    print(f"  Permanent TROs      : {total - temp_count}")
    print(f"  Temporary (TTROs)   : {temp_count}")
    print(f"  Output              : {output_path}")
    print(f"  File size           : {output_path.stat().st_size / 1024:.1f} KB")
    print("\n  By TRO type:")
    for tro_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {tro_type:<30} {count:>5}  ({count/total*100:.1f}%)")
    print("\n  By authority (top 5):")
    for auth, count in authority_counts.most_common(5):
        print(f"    {auth:<40} {count:>5}")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main(sys.argv[1:])
