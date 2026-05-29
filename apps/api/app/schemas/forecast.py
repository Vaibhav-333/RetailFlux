from pydantic import BaseModel


class ForecastPoint(BaseModel):
    ds: str           # "YYYY-MM-DD"
    yhat: float
    yhat_lower: float
    yhat_upper: float


class SkuForecast(BaseModel):
    sku: str
    points: list[ForecastPoint]


class ForecastOut(BaseModel):
    forecasts: list[SkuForecast]
