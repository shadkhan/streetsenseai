"""CR-001 — Corridor seeding script.

Populates the corridors table from OS Open Roads (primary) with automatic
fallback to synthetic data when the OS API is unavailable.

Usage:
    uv run python -m tasks.seed_corridors                     # auto (OS with fallback)
    uv run python -m tasks.seed_corridors --source synthetic  # synthetic only
    uv run python -m tasks.seed_corridors --source os         # OS only, no fallback

Run once at deploy time, or again to refresh OS geometries.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


async def seed_corridors(source: str = "auto") -> dict[str, int]:
    """Seed the corridors table. Returns counts of OS-sourced and synthetic corridors."""
    import redis.asyncio as aioredis

    from config import settings
    from database import async_session_factory
    from services.corridor_repository import count_corridors, upsert_corridor
    from services.os_open_roads import OSOpenRoadsClient
    from services.synthetic.corridor_generator import SyntheticCorridorGenerator

    _REFS = Path(__file__).parent.parent / "services" / "synthetic" / "refs" / "corridors.json"
    definitions = json.loads(_REFS.read_text(encoding="utf-8"))

    syn_gen = SyntheticCorridorGenerator(seed=42)
    synthetic_map = {c.id: c for c in syn_gen.generate_all()}

    r: aioredis.Redis = aioredis.from_url(settings.redis_url)
    os_count = 0
    syn_count = 0

    try:
        async with OSOpenRoadsClient(r) as os_client:
            async with async_session_factory() as session:
                for defn in definitions:
                    corridor_id: str = defn["id"]
                    corridor = None

                    if source in ("os", "auto"):
                        corridor = await os_client.build_corridor(
                            corridor_id=corridor_id,
                            name=defn["name"],
                            road_name=defn["road_name"],
                            road_classification=defn["road_classification"],
                            centre_lng=defn["centre_lng"],
                            centre_lat=defn["centre_lat"],
                            length_km=defn["length_km"],
                        )
                        if corridor is not None:
                            os_count += 1
                            label = "OS"
                        elif source == "os":
                            print(f"  {corridor_id}: SKIPPED (OS returned no data, no fallback)")
                            continue

                    if corridor is None and source in ("synthetic", "auto"):
                        corridor = synthetic_map.get(corridor_id)
                        if corridor:
                            syn_count += 1
                            label = "SYNTHETIC"

                    if corridor is None:
                        print(f"  {corridor_id}: SKIPPED (no data)")
                        continue

                    await upsert_corridor(session, corridor)
                    print(f"  {corridor_id}: {label}")

                total = await count_corridors(session)
    finally:
        await r.aclose()

    return {"os": os_count, "synthetic": syn_count, "total": total}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="seed_corridors",
        description="Seed the corridors table (OS Open Roads with synthetic fallback).",
    )
    parser.add_argument(
        "--source",
        choices=["auto", "os", "synthetic"],
        default="auto",
        help="Data source: auto=OS with synthetic fallback, os=OS only, synthetic=synthetic only",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    print(f"Seeding corridors (source={args.source})...")

    result = asyncio.run(seed_corridors(source=args.source))

    print(f"\nDone: {result['total']} corridors total")
    print(f"  From OS Open Roads : {result['os']}")
    print(f"  From synthetic     : {result['synthetic']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main(sys.argv[1:])
