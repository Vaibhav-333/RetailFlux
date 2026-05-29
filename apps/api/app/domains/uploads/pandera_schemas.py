"""Pandera column schemas for each department upload format."""
import pandera as pa

_sales = pa.DataFrameSchema(
    {
        "date": pa.Column(str, nullable=False),
        "product_id": pa.Column(str, nullable=False),
        "sku": pa.Column(str, nullable=False),
        "quantity": pa.Column(int, pa.Check.greater_than(0), coerce=True),
        "revenue": pa.Column(float, pa.Check.greater_than_or_equal_to(0), coerce=True),
        "region": pa.Column(str, nullable=True, required=False),
    },
    coerce=True,
)

_marketing = pa.DataFrameSchema(
    {
        "date": pa.Column(str, nullable=False),
        "campaign_id": pa.Column(str, nullable=False),
        "spend": pa.Column(float, pa.Check.greater_than_or_equal_to(0), coerce=True),
        "impressions": pa.Column(int, pa.Check.greater_than_or_equal_to(0), coerce=True),
        "clicks": pa.Column(int, pa.Check.greater_than_or_equal_to(0), coerce=True),
        "conversions": pa.Column(int, pa.Check.greater_than_or_equal_to(0), coerce=True, nullable=True, required=False),
    },
    coerce=True,
)

_operations = pa.DataFrameSchema(
    {
        "date": pa.Column(str, nullable=False),
        "sku": pa.Column(str, nullable=False),
        "warehouse": pa.Column(str, nullable=False),
        "stock_level": pa.Column(int, pa.Check.greater_than_or_equal_to(0), coerce=True),
        "reorder_point": pa.Column(int, pa.Check.greater_than_or_equal_to(0), coerce=True),
    },
    coerce=True,
)

_finance = pa.DataFrameSchema(
    {
        "date": pa.Column(str, nullable=False),
        "category": pa.Column(str, nullable=False),
        "revenue": pa.Column(float, coerce=True),
        "cogs": pa.Column(float, pa.Check.greater_than_or_equal_to(0), coerce=True),
        "gross_profit": pa.Column(float, coerce=True),
    },
    coerce=True,
)

_procurement = pa.DataFrameSchema(
    {
        "date": pa.Column(str, nullable=False),
        "supplier_id": pa.Column(str, nullable=False),
        "sku": pa.Column(str, nullable=False),
        "quantity": pa.Column(int, pa.Check.greater_than(0), coerce=True),
        "unit_cost": pa.Column(float, pa.Check.greater_than(0), coerce=True),
        "lead_days": pa.Column(int, pa.Check.greater_than_or_equal_to(0), coerce=True, nullable=True, required=False),
    },
    coerce=True,
)

DEPT_SCHEMAS: dict[str, pa.DataFrameSchema] = {
    "sales": _sales,
    "marketing": _marketing,
    "operations": _operations,
    "finance": _finance,
    "procurement": _procurement,
}
