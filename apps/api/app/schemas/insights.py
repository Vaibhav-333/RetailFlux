from pydantic import BaseModel


class InsightItem(BaseModel):
    dept: str   # "sales" | "marketing" | "operations" | "finance" | "procurement"
    text: str


class AnomalyPoint(BaseModel):
    date: str
    revenue: float
    z_score: float


class InsightsOut(BaseModel):
    summary: str
    insights: list[InsightItem]
    generated_by: str   # "gemini" | "groq" | "fallback"
