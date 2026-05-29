from pydantic import BaseModel


class AlertPrefsOut(BaseModel):
    email_alerts_enabled: bool
    alert_on_anomalies: bool
    alert_on_low_stock: bool


class AlertPrefsUpdate(BaseModel):
    email_alerts_enabled: bool | None = None
    alert_on_anomalies: bool | None = None
    alert_on_low_stock: bool | None = None


class AlertCheckResult(BaseModel):
    anomalies_found: int
    low_stock_skus_found: int
    emails_sent: int
    notifications_created: int
