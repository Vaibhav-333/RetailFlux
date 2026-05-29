import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle,
  ChevronRight,
  BarChart3,
  Bell,
  Users,
  Sparkles,
  Package,
  ClipboardList,
  TrendingUp,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { updateOnboardingStepApi } from "@/features/users/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface WizardStep {
  id: number;
  title: string;
  description: string;
  icon: React.ElementType;
}

const STEPS: WizardStep[] = [
  {
    id: 1,
    title: "Welcome to RetailFlux",
    description: "Your AI-powered retail operating system. Choose how to get started.",
    icon: Sparkles,
  },
  {
    id: 2,
    title: "Explore your Master Dashboard",
    description: "The Master Dashboard gives you a live view of all departments at a glance.",
    icon: BarChart3,
  },
  {
    id: 3,
    title: "Turn insights into action",
    description: "Create tasks from any KPI card or anomaly — and track them to completion.",
    icon: ClipboardList,
  },
  {
    id: 4,
    title: "Inventory Intelligence",
    description: "ABC/XYZ analysis, reorder queue, and SKU drill-down with AI explanations.",
    icon: Package,
  },
  {
    id: 5,
    title: "Meet your AI Copilot",
    description: "Ask anything about your data. Press ⌘J to summon it on any page.",
    icon: Sparkles,
  },
  {
    id: 6,
    title: "Scenario Planner",
    description: "Simulate demand shocks, price changes, and marketing spend before committing.",
    icon: TrendingUp,
  },
  {
    id: 7,
    title: "Set your alert preferences",
    description: "Get notified about anomalies and low-stock events that need your attention.",
    icon: Bell,
  },
  {
    id: 8,
    title: "Invite your team",
    description: "Add team members and assign them department-specific roles.",
    icon: Users,
  },
];

const COMPLETED_STEP = 9;

// ─── Step content panels ──────────────────────────────────────────────────────

function Step1() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        RetailFlux aggregates sales, marketing, operations, finance, and procurement data into
        one platform powered by AI insights and real-time alerts.
      </p>
      <div className="grid grid-cols-1 gap-2 mt-4">
        {[
          { label: "Demo data", desc: "Use pre-loaded fashion retail data to explore dashboards immediately." },
          { label: "Upload your own", desc: "Upload CSV files for each department and see your real numbers.", to: "/dashboard/uploads" },
        ].map((opt) => (
          <div
            key={opt.label}
            className="flex items-start gap-3 p-3 rounded-lg border border-border hover:border-brand-400 hover:bg-brand-50/30 dark:hover:bg-brand-900/10 transition-colors cursor-default"
          >
            <CheckCircle className="w-4 h-4 text-brand-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-foreground">{opt.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{opt.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Step2() {
  const tiles = [
    { label: "Revenue", color: "bg-indigo-500" },
    { label: "ROAS", color: "bg-emerald-500" },
    { label: "Stock health", color: "bg-amber-500" },
    { label: "Gross margin", color: "bg-violet-500" },
    { label: "Procurement", color: "bg-blue-500" },
  ];
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Each KPI card links directly to its department dashboard. Click any card to drill into
        the full analytics view with charts, trends, and AI explanations.
      </p>
      <div className="grid grid-cols-5 gap-1.5">
        {tiles.map((t) => (
          <div
            key={t.label}
            className={cn("rounded-md h-14 flex items-end p-2 text-white text-[10px] font-medium opacity-80", t.color)}
          >
            {t.label}
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Tip: press <kbd className="px-1 py-0.5 rounded border border-border bg-muted text-[10px] font-mono">⌘K</kbd> to open
        the command palette and jump anywhere instantly.
      </p>
    </div>
  );
}

function Step3() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        RetailFlux can email you when anomalies are detected in your revenue or when SKU stock
        drops below reorder points.
      </p>
      <div className="space-y-2">
        {["Revenue anomalies (z-score &gt; 2.5σ)", "Low-stock SKU alerts", "Weekly performance digest"].map((item) => (
          <div key={item} className="flex items-center gap-2.5 p-2.5 rounded-lg bg-muted/50">
            <Bell className="w-4 h-4 text-brand-500 shrink-0" />
            <span className="text-sm text-foreground" dangerouslySetInnerHTML={{ __html: item }} />
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        Adjust these anytime in <strong>Settings → Email Alerts</strong>.
      </p>
    </div>
  );
}

function Step4() {
  const roles = [
    { role: "CEO", color: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400" },
    { role: "Admin", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" },
    { role: "Sales", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" },
    { role: "Finance", color: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" },
    { role: "Operations", color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
  ];
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Each team member only sees the data relevant to their role. Invite people from
        <strong> Settings → Team Members</strong>.
      </p>
      <div className="flex flex-wrap gap-2 mt-1">
        {roles.map(({ role, color }) => (
          <span key={role} className={cn("px-2.5 py-1 rounded-full text-xs font-semibold", color)}>
            {role}
          </span>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        7 roles available: CEO, Admin, Sales, Marketing, Finance, Operations, Procurement.
      </p>
    </div>
  );
}

// ── New step panels for v3 features ──────────────────────────────────────────

function Step3Tasks() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Every KPI card, anomaly alert, and inventory warning has a "Create Task" button. Tasks
        are tracked end-to-end — from creation through approval to measured outcome.
      </p>
      <div className="space-y-2 mt-2">
        {[
          { label: "Kanban board", desc: "Drag tasks across status columns: Open → In Progress → Done." },
          { label: "AI recommendations", desc: "RetailFlux auto-suggests tasks when anomalies are detected." },
          { label: "KPI links", desc: "Each task tracks its impact on the metric that triggered it." },
        ].map((item) => (
          <div key={item.label} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-muted/50">
            <CheckCircle className="w-4 h-4 text-brand-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-foreground">{item.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Navigate to <strong>Tasks → Board</strong> or click "Create Task" on any KPI card to get started.
      </p>
    </div>
  );
}

function Step4Inventory() {
  const segments = [
    { label: "AX", desc: "High revenue · Stable demand", color: "bg-emerald-500" },
    { label: "BY", desc: "Mid revenue · Variable demand", color: "bg-amber-500" },
    { label: "CZ", desc: "Low revenue · Erratic demand", color: "bg-red-500" },
  ];
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        The Inventory dashboard runs automatic ABC/XYZ segmentation, reorder math (EOQ + safety
        stock), and an AI health score per SKU — all updated nightly.
      </p>
      <div className="grid grid-cols-3 gap-2 mt-2">
        {segments.map((s) => (
          <div key={s.label} className={cn("rounded-lg p-3 text-white", s.color)}>
            <p className="text-sm font-bold">{s.label}</p>
            <p className="text-[10px] opacity-90 mt-0.5">{s.desc}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Accept a reorder recommendation to instantly create a procurement task.
        Navigate to <strong>Inventory</strong> in the sidebar.
      </p>
    </div>
  );
}

function Step5Copilot() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        The AI Copilot is grounded in <em>your</em> company's live data — not generic internet
        knowledge. It can answer questions, run simulations, and propose actions.
      </p>
      <div className="rounded-xl border border-border bg-muted/30 p-4 space-y-2">
        {[
          "Why did gross margin drop last week?",
          "Which SKUs should I reorder before Diwali?",
          "Simulate a -15% demand shock on our top category.",
        ].map((q) => (
          <div key={q} className="flex items-start gap-2">
            <Sparkles className="w-3.5 h-3.5 text-violet-500 mt-0.5 shrink-0" />
            <p className="text-xs text-foreground italic">"{q}"</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Press <kbd className="px-1 py-0.5 rounded border border-border bg-muted text-[10px] font-mono">⌘J</kbd> on any page to open the Copilot dock, or visit <strong>Copilot</strong> for full conversation history.
      </p>
    </div>
  );
}

function Step6Scenarios() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        The Scenario Planner is your retail digital twin. Adjust assumptions and instantly see
        the projected impact on revenue, margin, inventory, and cash.
      </p>
      <div className="grid grid-cols-2 gap-2 mt-1">
        {[
          { label: "Demand shock", example: "-20% units sold in Sept" },
          { label: "Price change", example: "+10% across tops category" },
          { label: "Marketing boost", example: "+$50K ad spend in Q4" },
          { label: "Lead time risk", example: "Supplier delays +14 days" },
        ].map((s) => (
          <div key={s.label} className="rounded-lg border border-border p-2.5">
            <p className="text-xs font-semibold text-foreground">{s.label}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{s.example}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        You can also ask the Copilot to "simulate a 20% demand drop" — it will hand off to the Scenario Planner automatically.
      </p>
    </div>
  );
}

const STEP_CONTENT: Record<number, () => React.JSX.Element> = {
  1: Step1,
  2: Step2,
  3: Step3Tasks,
  4: Step4Inventory,
  5: Step5Copilot,
  6: Step6Scenarios,
  7: Step3,        // existing alert prefs panel (renumbered)
  8: Step4,        // existing invite team panel (renumbered)
};

// ─── Main wizard ──────────────────────────────────────────────────────────────

interface OnboardingWizardProps {
  onComplete: () => void;
}

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState(1);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const totalSteps = STEPS.length;

  const { mutate: saveStep } = useMutation({
    mutationFn: (s: number) => updateOnboardingStepApi(s),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });

  function advance() {
    saveStep(step);
    if (step < totalSteps) {
      setStep((s) => s + 1);
    } else {
      saveStep(COMPLETED_STEP);
      onComplete();
      navigate("/dashboard");
    }
  }

  function dismiss() {
    saveStep(COMPLETED_STEP);
    onComplete();
  }

  const currentStepDef = STEPS[step - 1];
  const StepIcon = currentStepDef.icon;
  const StepContent = STEP_CONTENT[step];

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" aria-hidden="true" />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
        className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-card border border-border rounded-2xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-6 pb-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-brand-100 dark:bg-brand-900/40 p-2.5">
              <StepIcon className="w-5 h-5 text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                Step {step} of {totalSteps}
              </p>
              <h2 id="onboarding-title" className="text-base font-semibold text-foreground mt-0.5">
                {currentStepDef.title}
              </h2>
            </div>
          </div>
          <button
            onClick={dismiss}
            className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md focus-visible:ring-2 focus-visible:ring-brand-500 outline-none"
            aria-label="Skip onboarding"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="h-0.5 bg-muted mx-6 rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-500 transition-all duration-300"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>

        {/* Content */}
        <div className="px-6 py-5">{StepContent && <StepContent />}</div>

        {/* Step dots */}
        <div className="flex items-center justify-center gap-1.5 pb-2">
          {STEPS.map((s) => (
            <span
              key={s.id}
              className={cn(
                "inline-block rounded-full transition-all",
                s.id === step
                  ? "w-5 h-1.5 bg-brand-500"
                  : s.id < step
                  ? "w-1.5 h-1.5 bg-brand-300"
                  : "w-1.5 h-1.5 bg-muted-foreground/30",
              )}
            />
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-muted/20">
          <button
            onClick={dismiss}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 rounded outline-none"
          >
            Skip for now
          </button>
          <button
            onClick={advance}
            className="inline-flex items-center gap-2 px-5 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-background outline-none"
          >
            {step === totalSteps ? "Get started" : "Next"}
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </>
  );
}
