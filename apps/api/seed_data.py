"""Seed the database with sample street works for SM-006 API testing.

Usage (from apps/api/):
    uv run python seed_data.py

Prerequisites:
    1. Docker stack running:   cd infra && docker-compose up -d
    2. Migrations applied:     uv run alembic upgrade head
    3. .env.local present with DATABASE_URL set (Docker default is fine)

Sample data covers three UK city clusters so you can test every endpoint:

  Birmingham bbox: min_lon=-1.92  min_lat=52.46  max_lon=-1.88  max_lat=52.50
  London bbox:     min_lon=-0.14  min_lat=51.50  max_lon=-0.12  max_lat=51.52
  Manchester bbox: min_lon=-2.25  min_lat=53.46  max_lon=-2.21  max_lat=53.49

  USRN 41507223 = Corporation Street, Birmingham (2 permits)
  USRN 21503001 = Oxford Street, London           (2 permits)
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta

# Allow importing from the apps/api package root
sys.path.insert(0, ".")

from database import async_session_factory  # noqa: E402
from schemas.domain import LineStringGeometry, PointGeometry, StreetWork  # noqa: E402
from services.works_repository import upsert_work  # noqa: E402

today = date.today()


def _d(offset: int) -> str:
    """Return today + offset days as an ISO date string."""
    return str(today + timedelta(days=offset))


SAMPLE_WORKS: list[StreetWork] = [
    # ── Birmingham City Centre ─────────────────────────────────────────────────
    # All five fall inside bbox: min_lon=-1.92, min_lat=52.46, max_lon=-1.88, max_lat=52.50

    StreetWork(
        permit_reference="WG7/2025/04001",
        usrn="41507223",
        street_name="Corporation Street",
        authority="Birmingham City Council",
        promoter="Cadent Gas",
        promoter_licence_number="WG7",
        work_type="Standard",
        traffic_management_type="Two-way signals",
        restriction_type="Lane closure",
        proposed_start_date=_d(-7),
        proposed_end_date=_d(7),
        actual_start_date=f"{_d(-7)}T08:00:00Z",
        status="in_progress",
        geometry=PointGeometry(type="Point", coordinates=(-1.8985, 52.4830)),
    ),

    StreetWork(
        permit_reference="WG7/2025/04002",
        usrn="41507223",          # same USRN — second permit on Corporation Street
        street_name="Corporation Street",
        authority="Birmingham City Council",
        promoter="Virgin Media",
        promoter_licence_number="VM1",
        work_type="Minor",
        traffic_management_type="Stop and go boards",
        restriction_type="Footway closure",
        proposed_start_date=_d(7),
        proposed_end_date=_d(30),
        status="granted",
        geometry=PointGeometry(type="Point", coordinates=(-1.8990, 52.4832)),
    ),

    StreetWork(
        permit_reference="WG7/2025/04003",
        usrn="41600001",
        street_name="Broad Street",
        authority="Birmingham City Council",
        promoter="BT Openreach",
        promoter_licence_number="BT1",
        work_type="Standard",
        traffic_management_type="Traffic control (multi-way signals)",
        restriction_type="Lane closure",
        proposed_start_date=_d(1),
        proposed_end_date=_d(8),
        status="granted",
        geometry=PointGeometry(type="Point", coordinates=(-1.9100, 52.4780)),
    ),

    StreetWork(
        permit_reference="WG7/2025/04004",
        usrn="41600002",
        street_name="Bristol Road",
        authority="Birmingham City Council",
        promoter="Severn Trent Water",
        promoter_licence_number="ST1",
        work_type="Major",
        traffic_management_type="Traffic control (multi-way signals)",
        restriction_type="Road closure",
        proposed_start_date=_d(-7),
        proposed_end_date=_d(30),
        actual_start_date=f"{_d(-7)}T07:30:00Z",
        status="in_progress",
        geometry=LineStringGeometry(      # A38 — only LineString in the sample set
            type="LineString",
            coordinates=[
                (-1.9050, 52.4620),
                (-1.9055, 52.4670),
                (-1.9060, 52.4720),
            ],
        ),
    ),

    StreetWork(
        permit_reference="WG7/2025/04005",
        usrn="41505001",
        street_name="Bull Street",
        authority="Birmingham City Council",
        promoter="National Grid",
        promoter_licence_number="NG1",
        work_type="Minor",
        traffic_management_type="Stop and go boards",
        restriction_type="Lane closure",
        proposed_start_date=_d(-21),
        proposed_end_date=_d(-1),
        actual_start_date=f"{_d(-21)}T09:00:00Z",
        actual_end_date=f"{_d(-1)}T17:00:00Z",
        status="completed",
        geometry=PointGeometry(type="Point", coordinates=(-1.8975, 52.4842)),
    ),

    # ── London (Oxford Street) ─────────────────────────────────────────────────
    # bbox: min_lon=-0.14, min_lat=51.50, max_lon=-0.12, max_lat=51.52

    StreetWork(
        permit_reference="NW9/2025/01001",
        usrn="21503001",
        street_name="Oxford Street",
        authority="Transport for London",
        promoter="Thames Water",
        promoter_licence_number="TW1",
        work_type="Standard",
        traffic_management_type="Traffic control (multi-way signals)",
        restriction_type="Lane closure",
        proposed_start_date=_d(-7),
        proposed_end_date=_d(7),
        actual_start_date=f"{_d(-7)}T06:00:00Z",
        status="in_progress",
        geometry=PointGeometry(type="Point", coordinates=(-0.1310, 51.5152)),
    ),

    StreetWork(
        permit_reference="NW9/2025/01002",
        usrn="21503001",          # same USRN — second permit on Oxford Street
        street_name="Oxford Street",
        authority="Transport for London",
        promoter="UK Power Networks",
        promoter_licence_number="UP1",
        work_type="Minor",
        traffic_management_type="Stop and go boards",
        restriction_type="Footway closure",
        proposed_start_date=_d(1),
        proposed_end_date=_d(8),
        status="granted",
        geometry=PointGeometry(type="Point", coordinates=(-0.1290, 51.5148)),
    ),

    # ── Manchester ─────────────────────────────────────────────────────────────
    # bbox: min_lon=-2.25, min_lat=53.46, max_lon=-2.21, max_lat=53.49

    StreetWork(
        permit_reference="MAN/2025/05001",
        usrn="41700001",
        street_name="Deansgate",
        authority="Manchester City Council",
        promoter="United Utilities",
        promoter_licence_number="UU1",
        work_type="Standard",
        traffic_management_type="Two-way signals",
        restriction_type="Lane closure",
        proposed_start_date=_d(0),
        proposed_end_date=_d(7),
        status="granted",
        geometry=PointGeometry(type="Point", coordinates=(-2.2472, 53.4784)),
    ),

    StreetWork(
        permit_reference="MAN/2025/05002",
        usrn="41700002",
        street_name="Market Street",
        authority="Manchester City Council",
        promoter="BT Openreach",
        promoter_licence_number="BT1",
        work_type="Minor",
        traffic_management_type="Stop and go boards",
        restriction_type="Footway closure",
        proposed_start_date=_d(7),
        proposed_end_date=_d(30),
        status="submitted",
        geometry=PointGeometry(type="Point", coordinates=(-2.2388, 53.4808)),
    ),
]


async def seed() -> None:
    print(f"Inserting {len(SAMPLE_WORKS)} sample works...\n")
    async with async_session_factory() as session:
        for work in SAMPLE_WORKS:
            await upsert_work(session, work)
            print(f"  [ok] {work.permit_reference:<22}  {work.street_name:<25}  {work.status}")

    print("\n--- Ready to test ---\n")
    print("Swagger UI (interactive):")
    print("  http://localhost:8000/docs\n")
    print("Single permit (slashes in the reference survive :path routing):")
    print("  GET http://localhost:8000/works/permit/WG7/2025/04001\n")
    print("Birmingham bbox (5 works — includes a LineString on Bristol Road):")
    print("  GET http://localhost:8000/works/bbox?min_lon=-1.92&min_lat=52.46&max_lon=-1.88&max_lat=52.50\n")
    print("Same bbox but only active works (status filter, multi-value):")
    print("  GET http://localhost:8000/works/bbox?min_lon=-1.92&min_lat=52.46&max_lon=-1.88&max_lat=52.50&status=granted&status=in_progress\n")
    print("Date range — works that overlap next 7 days:")
    print(f"  GET http://localhost:8000/works/bbox?min_lon=-1.92&min_lat=52.46&max_lon=-1.88&max_lat=52.50&from_date={_d(0)}&to_date={_d(7)}\n")
    print("USRN query — two permits on Corporation Street:")
    print("  GET http://localhost:8000/works/usrn/41507223\n")
    print("Authority query — all 5 Birmingham City Council works:")
    print("  GET http://localhost:8000/works/authority/Birmingham City Council\n")
    print("London bbox (2 works):")
    print("  GET http://localhost:8000/works/bbox?min_lon=-0.14&min_lat=51.50&max_lon=-0.12&max_lat=51.52\n")
    print("Manchester authority:")
    print("  GET http://localhost:8000/works/authority/Manchester City Council")


if __name__ == "__main__":
    asyncio.run(seed())
