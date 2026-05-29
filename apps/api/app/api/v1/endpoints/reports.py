from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.domains.auth.dependencies import get_current_user
from app.domains.reports.report_service import DeptLiteral, export_report
from app.models.user import User

router = APIRouter()


@router.get("/export", summary="Export department KPIs as CSV or JSON")
async def export_kpis(
    dept: DeptLiteral = Query(..., description="Department to export"),
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    fmt: Literal["csv", "json"] = Query("csv", description="Export format"),
    current_user: User = Depends(get_current_user),
) -> Response:
    content, filename = await export_report(
        company_id=str(current_user.company_id),
        dept=dept,
        date_from=date_from,
        date_to=date_to,
        fmt=fmt,
    )
    media_type = "text/csv" if fmt == "csv" else "application/json"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
