"""NC-001 – NC-006 — Non-Compliance Analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.compliance import (
    ComplianceSummary,
    FPNOpportunity,
    MonthlyTrend,
    PromoterComplianceRead,
)
from services.compliance import (
    compute_all_promoters,
    export_promoters_csv,
    get_compliance_summary,
    get_fpn_opportunities,
    get_monthly_trend,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get(
    "/summary",
    response_model=ComplianceSummary,
    response_model_by_alias=True,
    summary="Compliance dashboard summary (NC-002)",
)
async def compliance_summary(
    session: AsyncSession = Depends(get_db),
) -> ComplianceSummary:
    return await get_compliance_summary(session)


@router.get(
    "/promoters",
    response_model=list[PromoterComplianceRead],
    response_model_by_alias=True,
    summary="Promoter compliance league table (NC-003)",
    description=(
        "Returns all promoters sorted by compliance score ascending "
        "(worst offender first).  Optionally filter to a single region "
        "with ?region=<authority>."
    ),
)
async def list_promoters(
    region: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[PromoterComplianceRead]:
    promoters = await compute_all_promoters(session)
    if region:
        promoters = [p for p in promoters if p.region == region]
    return promoters


@router.get(
    "/promoters/{licence_number}/monthly-trend",
    response_model=list[MonthlyTrend],
    response_model_by_alias=True,
    summary="12-month compliance trend for a promoter (NC-004)",
)
async def promoter_monthly_trend(
    licence_number: str,
    months: int = 12,
    session: AsyncSession = Depends(get_db),
) -> list[MonthlyTrend]:
    return await get_monthly_trend(session, licence_number, months=min(months, 24))


@router.get(
    "/fpn-opportunities",
    response_model=list[FPNOpportunity],
    response_model_by_alias=True,
    summary="FPN opportunity candidates (NC-005)",
    description=(
        "Returns completed works that overran their proposed end date by "
        "at least 1 day, sorted by overrun duration descending."
    ),
)
async def fpn_opportunities(
    session: AsyncSession = Depends(get_db),
) -> list[FPNOpportunity]:
    return await get_fpn_opportunities(session)


@router.get(
    "/export/promoters.csv",
    summary="Export promoter compliance data as CSV (NC-006)",
    response_class=PlainTextResponse,
)
async def export_promoters(
    session: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    promoters = await compute_all_promoters(session)
    csv_content = export_promoters_csv(promoters)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=promoter-compliance.csv"},
    )


@router.get(
    "/briefing/generate",
    summary="AI monthly compliance briefing stream (NC-007 mock)",
    description="Streams a plain-English compliance briefing. "
                "Will be replaced by LangChain agent when API key is present.",
)
async def generate_briefing(
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    summary = await get_compliance_summary(session)
    promoters = await compute_all_promoters(session)
    fpn = await get_fpn_opportunities(session)

    worst = summary.worst_offender
    best = summary.best_performer

    briefing = (
        f"## Monthly Non-Compliance Briefing\n\n"
        f"This month's analysis covers **{summary.total_promoters} promoters** "
        f"operating across the network. "
        f"The average compliance score stands at **{summary.avg_compliance_score:.1f}/100**, "
        f"indicating {'healthy' if summary.avg_compliance_score >= 70 else 'concerning'} "
        f"overall network discipline.\n\n"
    )

    if worst:
        deteriorating = sum(1 for p in promoters if p.trend == "deteriorating")
        briefing += (
            f"**Worst performer this period** is {worst.promoter_name} "
            f"(licence {worst.promoter_licence_number}), "
            f"operating primarily in {worst.region}, "
            f"with a compliance score of **{worst.compliance_score:.1f}**. "
            f"Their overrun rate of {worst.overrun_rate * 100:.0f}% is a priority concern.\n\n"
        )
        if deteriorating:
            briefing += (
                f"**{deteriorating} promoter{'s' if deteriorating > 1 else ''} "
                f"show a deteriorating compliance trend** — "
                f"early intervention is recommended before further enforcement action.\n\n"
            )

    if fpn:
        briefing += (
            f"**{len(fpn)} FPN opportunities** have been identified this period. "
            f"The longest overrun is {fpn[0].overrun_days} days "
            f"on permit {fpn[0].permit_reference} "
            f"({fpn[0].street_name}, {fpn[0].authority}).\n\n"
        )

    if best:
        briefing += (
            f"**Best performer** is {best.promoter_name} "
            f"with a compliance score of {best.compliance_score:.1f}. "
            f"Their practices should be referenced as the benchmark.\n\n"
        )

    briefing += (
        f"*Based on Street Manager data · "
        f"Updated {summary.calculated_at[:10]}*"
    )

    async def streamer():
        words = briefing.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield chunk.encode()

    return StreamingResponse(streamer(), media_type="text/plain")
