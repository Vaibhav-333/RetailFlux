"""AI Chat service: routes natural-language questions to analytics tools via LLM."""
import json
import re

from app.core.gemini import generate_text
from app.domains.analytics.sales_service import get_sales_kpis
from app.domains.analytics.marketing_service import get_marketing_kpis
from app.domains.analytics.operations_service import get_operations_kpis
from app.domains.analytics.finance_service import get_finance_kpis
from app.domains.analytics.procurement_service import get_procurement_kpis
from app.domains.analytics.summary_service import get_dashboard_summary
from app.domains.insights.anomaly_service import get_revenue_anomalies
from app.domains.forecasting.top_skus_forecast import get_top_skus_forecast
from app.schemas.chat import ChatResponse


TOOL_REGISTRY = {
    "get_sales_kpis": {
        "fn": get_sales_kpis,
        "description": "Get sales KPIs: total revenue, order count, AOV, top SKUs, revenue by region, daily revenue trend.",
        "params": ["company_id"],
        "dept": "sales",
    },
    "get_marketing_kpis": {
        "fn": get_marketing_kpis,
        "description": "Get marketing KPIs: ad spend, ROAS, CAC, CTR, top campaigns, daily spend trend.",
        "params": ["company_id"],
        "dept": "marketing",
    },
    "get_operations_kpis": {
        "fn": get_operations_kpis,
        "description": "Get operations KPIs: total SKUs, stock units, warehouses, SKUs below reorder point, stock by warehouse.",
        "params": ["company_id"],
        "dept": "operations",
    },
    "get_finance_kpis": {
        "fn": get_finance_kpis,
        "description": "Get finance KPIs: revenue, COGS, gross profit, gross margin %, revenue by category, monthly P&L.",
        "params": ["company_id"],
        "dept": "finance",
    },
    "get_procurement_kpis": {
        "fn": get_procurement_kpis,
        "description": "Get procurement KPIs: total spend, units ordered, unique suppliers, avg lead days, top suppliers.",
        "params": ["company_id"],
        "dept": "procurement",
    },
    "get_dashboard_summary": {
        "fn": get_dashboard_summary,
        "description": "Get CEO dashboard summary combining KPIs from all 5 departments plus a revenue sparkline.",
        "params": ["company_id"],
        "dept": None,
    },
    "get_revenue_anomalies": {
        "fn": get_revenue_anomalies,
        "description": "Detect revenue anomalies (spikes/drops) using z-score analysis on daily revenue.",
        "params": ["company_id"],
        "dept": None,
    },
    "get_top_skus_forecast": {
        "fn": get_top_skus_forecast,
        "description": "Get 30-day demand forecast for top-5 revenue SKUs using Prophet time-series model.",
        "params": ["company_id"],
        "dept": None,
    },
}

ROLE_TOOL_ACCESS = {
    "ceo": None,
    "admin": None,
    "sales": {"get_sales_kpis", "get_dashboard_summary", "get_revenue_anomalies", "get_top_skus_forecast"},
    "marketing": {"get_marketing_kpis", "get_dashboard_summary"},
    "operations": {"get_operations_kpis", "get_dashboard_summary"},
    "finance": {"get_finance_kpis", "get_dashboard_summary"},
    "procurement": {"get_procurement_kpis", "get_dashboard_summary"},
}


def _get_available_tools(role: str) -> dict:
    allowed = ROLE_TOOL_ACCESS.get(role)
    if allowed is None:
        return TOOL_REGISTRY
    return {k: v for k, v in TOOL_REGISTRY.items() if k in allowed}


def _build_tool_selection_prompt(question: str, tools: dict) -> str:
    tool_descriptions = "\n".join(
        f'- "{name}": {info["description"]}' for name, info in tools.items()
    )
    return (
        "You are a retail analytics assistant. Based on the user's question, select the most "
        "appropriate tool to answer it. Respond ONLY with valid JSON, no markdown.\n\n"
        f"Available tools:\n{tool_descriptions}\n\n"
        f'User question: "{question}"\n\n'
        'Respond with: {"tool": "<tool_name>"}\n'
        "If the question cannot be answered by any tool, respond with: "
        '{"tool": null, "direct_answer": "<your answer>"}'
    )


def _build_answer_prompt(question: str, tool_name: str, data_json: str) -> str:
    return (
        "You are a retail analytics assistant. The user asked a question and we retrieved data.\n"
        "Provide a concise, insightful answer based on the data. Use specific numbers from the data. "
        "Format currency values. Keep the response under 200 words.\n\n"
        f'User question: "{question}"\n'
        f"Data source: {tool_name}\n"
        f"Data:\n{data_json[:3000]}\n\n"
        "Answer:"
    )


def _parse_json_response(text: str) -> dict | None:
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


async def handle_chat_message(company_id: str, role: str, message: str) -> ChatResponse:
    tools = _get_available_tools(role)

    selection_prompt = _build_tool_selection_prompt(message, tools)
    selection_text, provider = await generate_text(selection_prompt)

    parsed = _parse_json_response(selection_text)
    if not parsed or parsed.get("tool") is None:
        direct = parsed.get("direct_answer", selection_text) if parsed else selection_text
        return ChatResponse(answer=direct, tool_used=None, data=None, provider=provider)

    tool_name = parsed["tool"]
    if tool_name not in tools:
        return ChatResponse(
            answer=f"I don't have access to the '{tool_name}' tool for your role.",
            tool_used=None,
            data=None,
            provider=provider,
        )

    tool_info = tools[tool_name]
    tool_fn = tool_info["fn"]
    result = await tool_fn(company_id)

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    data_json = json.dumps(result_dict, default=str)

    answer_prompt = _build_answer_prompt(message, tool_name, data_json)
    answer_text, answer_provider = await generate_text(answer_prompt)

    return ChatResponse(
        answer=answer_text,
        tool_used=tool_name,
        data=result_dict,
        provider=answer_provider,
    )
