import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FileJson, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { type ReportDept, type ReportFormat, downloadReportApi } from "@/features/reports/api";
import { getSalesKpisApi } from "@/features/sales/api";
import { getMarketingKpisApi } from "@/features/marketing/api";
import { getOperationsKpisApi } from "@/features/operations/api";
import { getFinanceKpisApi } from "@/features/finance/api";
import { getProcurementKpisApi } from "@/features/procurement/api";

const DEPTS: { value: ReportDept; label: string; color: string }[] = [
  { value: "sales", label: "Sales", color: "bg-indigo-100 text-indigo-700 border-indigo-200" },
  { value: "marketing", label: "Marketing", color: "bg-pink-100 text-pink-700 border-pink-200" },
  { value: "operations", label: "Operations", color: "bg-amber-100 text-amber-700 border-amber-200" },
  { value: "finance", label: "Finance", color: "bg-green-100 text-green-700 border-green-200" },
  { value: "procurement", label: "Procurement", color: "bg-orange-100 text-orange-700 border-orange-200" },
];

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-xl font-semibold">{value}</p>
    </div>
  );
}

function DeptStats({ dept, dateFrom, dateTo }: { dept: ReportDept; dateFrom: string; dateTo: string }) {
  const salesQ = useQuery({
    queryKey: ["sales-kpis", dateFrom, dateTo],
    queryFn: () => getSalesKpisApi(dateFrom, dateTo),
    enabled: dept === "sales",
  });
  const mktQ = useQuery({
    queryKey: ["marketing-kpis", dateFrom, dateTo],
    queryFn: () => getMarketingKpisApi(dateFrom, dateTo),
    enabled: dept === "marketing",
  });
  const opsQ = useQuery({
    queryKey: ["operations-kpis", dateFrom, dateTo],
    queryFn: () => getOperationsKpisApi(dateFrom, dateTo),
    enabled: dept === "operations",
  });
  const finQ = useQuery({
    queryKey: ["finance-kpis", dateFrom, dateTo],
    queryFn: () => getFinanceKpisApi(dateFrom, dateTo),
    enabled: dept === "finance",
  });
  const procQ = useQuery({
    queryKey: ["procurement-kpis", dateFrom, dateTo],
    queryFn: () => getProcurementKpisApi(dateFrom, dateTo),
    enabled: dept === "procurement",
  });

  if (dept === "sales") {
    if (salesQ.isLoading) return <StatsLoading />;
    if (!salesQ.data) return null;
    const d = salesQ.data;
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Total Revenue" value={fmt(d.total_revenue)} />
        <StatTile label="Units Sold" value={d.total_units.toLocaleString()} />
        <StatTile label="Avg Order Value" value={fmt(d.aov)} />
        <StatTile label="Top SKU" value={d.top_sku ?? "—"} />
      </div>
    );
  }
  if (dept === "marketing") {
    if (mktQ.isLoading) return <StatsLoading />;
    if (!mktQ.data) return null;
    const d = mktQ.data;
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Total Spend" value={fmt(d.total_spend)} />
        <StatTile label="ROAS" value={`${d.roas.toFixed(2)}×`} />
        <StatTile label="Conversions" value={d.total_conversions.toLocaleString()} />
        <StatTile label="CTR" value={`${d.ctr.toFixed(2)}%`} />
      </div>
    );
  }
  if (dept === "operations") {
    if (opsQ.isLoading) return <StatsLoading />;
    if (!opsQ.data) return null;
    const d = opsQ.data;
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Total SKUs" value={d.total_skus.toLocaleString()} />
        <StatTile label="Stock Units" value={d.total_stock_units.toLocaleString()} />
        <StatTile label="Below Reorder" value={d.skus_below_reorder.toLocaleString()} />
        <StatTile label="Warehouses" value={d.active_warehouses.toLocaleString()} />
      </div>
    );
  }
  if (dept === "finance") {
    if (finQ.isLoading) return <StatsLoading />;
    if (!finQ.data) return null;
    const d = finQ.data;
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Revenue" value={fmt(d.total_revenue)} />
        <StatTile label="COGS" value={fmt(d.total_cogs)} />
        <StatTile label="Gross Profit" value={fmt(d.total_gross_profit)} />
        <StatTile label="Gross Margin" value={`${d.gross_margin.toFixed(1)}%`} />
      </div>
    );
  }
  if (dept === "procurement") {
    if (procQ.isLoading) return <StatsLoading />;
    if (!procQ.data) return null;
    const d = procQ.data;
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Total Spend" value={fmt(d.total_spend)} />
        <StatTile label="Units Ordered" value={d.total_units.toLocaleString()} />
        <StatTile label="Suppliers" value={d.unique_suppliers.toLocaleString()} />
        <StatTile label="Avg Lead Days" value={`${d.avg_lead_days.toFixed(1)}d`} />
      </div>
    );
  }
  return null;
}

function StatsLoading() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-20 animate-pulse rounded-lg bg-muted" />
      ))}
    </div>
  );
}

export function ReportsPage() {
  const defaultFrom = new Date(Date.now() - 90 * 86_400_000).toISOString().slice(0, 10);
  const defaultTo = new Date().toISOString().slice(0, 10);

  const [dept, setDept] = useState<ReportDept>("sales");
  const [dateFrom, setDateFrom] = useState(defaultFrom);
  const [dateTo, setDateTo] = useState(defaultTo);
  const [downloading, setDownloading] = useState(false);

  async function handleDownload(fmt: ReportFormat) {
    setDownloading(true);
    try {
      await downloadReportApi({ dept, date_from: dateFrom, date_to: dateTo, fmt });
      toast.success(`${dept} report downloaded as ${fmt.toUpperCase()}`);
    } catch {
      toast.error("Download failed. Please try again.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Reports & Exports</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Download department KPI data as CSV (for Excel) or JSON (for developers).
        </p>
      </div>

      {/* Export card */}
      <div className="rounded-lg border bg-card p-6 shadow-sm space-y-5">
        <h2 className="text-base font-semibold">Export Configuration</h2>

        {/* Department selector */}
        <div>
          <label className="mb-2 block text-sm font-medium">Department</label>
          <div className="flex flex-wrap gap-2">
            {DEPTS.map((d) => (
              <button
                key={d.value}
                onClick={() => setDept(d.value)}
                className={`rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
                  dept === d.value ? d.color : "border-border text-muted-foreground hover:border-foreground"
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        {/* Date range */}
        <div>
          <label className="mb-2 block text-sm font-medium">Date Range</label>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded border px-3 py-1.5 text-sm"
            />
            <span className="text-muted-foreground">–</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded border px-3 py-1.5 text-sm"
            />
          </div>
        </div>

        {/* Download buttons */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => handleDownload("csv")}
            disabled={downloading}
            className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-60"
          >
            {downloading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileText className="h-4 w-4" />
            )}
            Download CSV
          </button>
          <button
            onClick={() => handleDownload("json")}
            disabled={downloading}
            className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-4 py-2 text-sm font-medium shadow-sm hover:bg-muted disabled:opacity-60"
          >
            {downloading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileJson className="h-4 w-4" />
            )}
            Download JSON
          </button>
        </div>
      </div>

      {/* Live KPI preview */}
      <div className="rounded-lg border bg-card p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Download className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold">
            {DEPTS.find((d) => d.value === dept)?.label} KPI Preview
          </h2>
        </div>
        <p className="text-xs text-muted-foreground">
          CSV export contains the daily time-series. JSON export contains the full KPI object.
        </p>
        <DeptStats dept={dept} dateFrom={dateFrom} dateTo={dateTo} />
      </div>
    </div>
  );
}
