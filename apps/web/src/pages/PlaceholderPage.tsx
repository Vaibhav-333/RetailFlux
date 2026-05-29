import { Construction } from "lucide-react";

interface PlaceholderPageProps {
  dept: string;
  session: number;
}

export function PlaceholderPage({ dept, session }: PlaceholderPageProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center animate-fade-in">
      <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center">
        <Construction className="w-7 h-7 text-muted-foreground" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-foreground">{dept} Dashboard</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Scheduled for <span className="font-medium text-brand-500">Session {session}</span>
        </p>
      </div>
      <p className="text-xs text-muted-foreground max-w-xs">
        This dashboard will include full KPIs, interactive charts, AI-generated insights,
        and drill-down analytics. See <code className="font-mono">RETAILFLUX_PLAN.md</code> for the complete spec.
      </p>
    </div>
  );
}
