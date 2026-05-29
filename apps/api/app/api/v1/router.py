from fastapi import APIRouter

from app.api.v1.endpoints.alerts import router as alerts_router
from app.api.v1.endpoints.scenarios import router as scenarios_router
from app.api.v1.endpoints.inventory import router as inventory_router
from app.api.v1.endpoints.pricing import router as pricing_router
from app.api.v1.endpoints.profit import router as profit_router
from app.api.v1.endpoints.purchase_orders import router as purchase_orders_router
from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.cache import router as cache_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.copilot import router as copilot_router
from app.api.v1.endpoints.forecasting import router as forecasting_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.insights import router as insights_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.observability import router as observability_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.uploads import router as uploads_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.feature_flags import router as feature_flags_router
from app.api.v1.endpoints.ws import router as ws_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(uploads_router, prefix="/uploads", tags=["Uploads"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(insights_router, prefix="/insights", tags=["Insights"])
api_router.include_router(forecasting_router, prefix="/forecasting", tags=["Forecasting"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(observability_router, prefix="/observability", tags=["Observability"])
api_router.include_router(audit_router, prefix="/audit", tags=["Audit"])
api_router.include_router(cache_router, prefix="/cache", tags=["Cache"])
api_router.include_router(copilot_router, prefix="/copilot", tags=["Copilot"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(profit_router, prefix="/profit", tags=["Profit Intelligence"])
api_router.include_router(pricing_router, prefix="/pricing", tags=["Dynamic Pricing"])
api_router.include_router(purchase_orders_router, prefix="/purchase-orders", tags=["Purchase Orders"])
api_router.include_router(scenarios_router, prefix="/scenarios", tags=["Scenarios"])
api_router.include_router(feature_flags_router, prefix="/feature-flags", tags=["Feature Flags"])
api_router.include_router(ws_router, tags=["WebSocket"])
