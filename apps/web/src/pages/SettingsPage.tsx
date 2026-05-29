import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  User,
  Bell,
  Building2,
  Palette,
  Play,
  Save,
  Shield,
  Users,
  UserPlus,
  X,
  ChevronDown,
} from "lucide-react";
import { useAuthStore } from "@/features/auth/authStore";
import { usePrefs } from "@/state/PrefsContext";
import { updateUserApi } from "@/features/auth/api";
import {
  listUsersApi,
  createUserApi,
  adminUpdateUserApi,
} from "@/features/users/api";
import {
  getAlertPrefsApi,
  updateAlertPrefsApi,
  checkAlertsApi,
} from "@/features/alerts/api";
import type { User as UserType, UserRole, AlertPrefs } from "@/types";
import { cn } from "@/lib/utils";

const ALL_ROLES: UserRole[] = [
  "ceo", "admin", "sales", "marketing", "finance", "operations", "procurement",
];

const ROLE_COLORS: Record<UserRole, string> = {
  ceo: "bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-900/20 dark:text-violet-300 dark:border-violet-800",
  admin: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800",
  sales: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-800",
  marketing: "bg-pink-50 text-pink-700 border-pink-200 dark:bg-pink-900/20 dark:text-pink-300 dark:border-pink-800",
  finance: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-800",
  operations: "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/20 dark:text-orange-300 dark:border-orange-800",
  procurement: "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-900/20 dark:text-teal-300 dark:border-teal-800",
};

function SectionCard({
  icon: Icon,
  title,
  action,
  children,
}: {
  icon: React.ElementType;
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      {children}
    </div>
  );
}

function Initials({ name }: { name: string }) {
  const letters = name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
  return (
    <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center shrink-0">
      <span className="text-xs font-semibold text-brand-700 dark:text-brand-300">{letters}</span>
    </div>
  );
}

function UserRow({
  user,
  isSelf,
  onRoleChange,
  onToggleActive,
}: {
  user: UserType;
  isSelf: boolean;
  onRoleChange: (id: string, role: UserRole) => void;
  onToggleActive: (id: string, active: boolean) => void;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 py-3 px-1 border-b border-border last:border-0",
        !user.is_active && "opacity-50"
      )}
    >
      <Initials name={user.name} />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">
          {user.name}
          {isSelf && (
            <span className="ml-2 text-xs text-muted-foreground font-normal">(you)</span>
          )}
        </p>
        <p className="text-xs text-muted-foreground truncate">{user.email}</p>
      </div>

      {/* Role selector */}
      <div className="relative">
        <select
          value={user.role}
          disabled={isSelf}
          onChange={(e) => onRoleChange(user.id, e.target.value as UserRole)}
          className={cn(
            "appearance-none text-xs font-medium px-2.5 py-1 pr-6 rounded-full border cursor-pointer",
            "bg-transparent focus:outline-none focus:ring-2 focus:ring-brand-500",
            "disabled:cursor-not-allowed",
            ROLE_COLORS[user.role as UserRole] ?? ROLE_COLORS.sales
          )}
        >
          {ALL_ROLES.map((r) => (
            <option key={r} value={r} className="bg-background text-foreground">
              {r}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 pointer-events-none opacity-60" />
      </div>

      {/* Active toggle */}
      <button
        disabled={isSelf}
        onClick={() => onToggleActive(user.id, !user.is_active)}
        className={cn(
          "text-xs px-2.5 py-1 rounded-full border font-medium transition-colors disabled:cursor-not-allowed",
          user.is_active
            ? "bg-green-50 text-green-700 border-green-200 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800"
            : "bg-muted text-muted-foreground border-border hover:bg-accent"
        )}
      >
        {user.is_active ? "Active" : "Inactive"}
      </button>

      {/* Last login */}
      <span className="text-xs text-muted-foreground w-20 text-right shrink-0 hidden sm:block">
        {user.last_login_at
          ? new Date(user.last_login_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            })
          : "Never"}
      </span>
    </div>
  );
}

function InviteForm({ onSuccess }: { onSuccess: () => void }) {
  const [form, setForm] = useState({
    name: "",
    email: "",
    role: "sales" as UserRole,
    password: "",
  });

  const mutation = useMutation({
    mutationFn: () => createUserApi(form),
    onSuccess: () => {
      toast.success(`${form.name} has been added to your team`);
      setForm({ name: "", email: "", role: "sales", password: "" });
      onSuccess();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err.response?.data?.detail ?? "Failed to add user");
    },
  });

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((p) => ({ ...p, [k]: e.target.value }));

  const inputCls =
    "h-9 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-brand-500";

  return (
    <div className="mt-4 pt-4 border-t border-border">
      <p className="text-xs font-semibold text-foreground mb-3">Add Team Member</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Field label="Full Name">
          <input className={inputCls} placeholder="Jane Smith" value={form.name} onChange={set("name")} />
        </Field>
        <Field label="Email">
          <input className={inputCls} type="email" placeholder="jane@company.com" value={form.email} onChange={set("email")} />
        </Field>
        <Field label="Role">
          <select
            className={inputCls}
            value={form.role}
            onChange={set("role")}
          >
            {ALL_ROLES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </Field>
        <Field label="Temporary Password">
          <input className={inputCls} type="password" placeholder="Min. 8 characters" value={form.password} onChange={set("password")} />
        </Field>
      </div>
      <div className="flex items-center gap-2 mt-3">
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !form.name || !form.email || form.password.length < 8}
          className="inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          {mutation.isPending ? "Adding…" : "Add Member"}
        </button>
      </div>
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3 border-b border-border last:border-0">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        {description && (
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
        )}
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200",
          checked ? "bg-brand-600" : "bg-muted-foreground/30"
        )}
      >
        <span
          className={cn(
            "inline-block h-4 w-4 rounded-full bg-white shadow transition-transform duration-200",
            checked ? "translate-x-4" : "translate-x-0"
          )}
        />
      </button>
    </div>
  );
}

function EmailAlertsSection({ isCeoOrAdmin }: { isCeoOrAdmin: boolean }) {
  const qc = useQueryClient();

  const { data: prefs, isLoading } = useQuery<AlertPrefs>({
    queryKey: ["alert-prefs"],
    queryFn: getAlertPrefsApi,
  });

  const updateMutation = useMutation({
    mutationFn: (patch: Partial<AlertPrefs>) => updateAlertPrefsApi(patch),
    onSuccess: (updated) => {
      qc.setQueryData(["alert-prefs"], updated);
    },
    onError: () => toast.error("Failed to save alert preferences"),
  });

  const checkMutation = useMutation({
    mutationFn: checkAlertsApi,
    onSuccess: (result) => {
      const msg =
        result.emails_sent > 0
          ? `${result.emails_sent} email${result.emails_sent > 1 ? "s" : ""} sent — ${result.anomalies_found} anomal${result.anomalies_found === 1 ? "y" : "ies"}, ${result.low_stock_skus_found} low-stock SKUs`
          : "No active alerts at this time";
      toast.success(msg);
    },
    onError: () => toast.error("Alert check failed"),
  });

  const toggle = (key: keyof AlertPrefs) => (value: boolean) =>
    updateMutation.mutate({ [key]: value });

  return (
    <SectionCard
      icon={Bell}
      title="Email Alerts"
      action={
        isCeoOrAdmin ? (
          <button
            onClick={() => checkMutation.mutate()}
            disabled={checkMutation.isPending}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 transition-colors disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            {checkMutation.isPending ? "Checking…" : "Run Check"}
          </button>
        ) : undefined
      }
    >
      {isLoading ? (
        <div className="flex justify-center py-6">
          <div className="animate-spin h-5 w-5 rounded-full border-2 border-brand-500 border-t-transparent" />
        </div>
      ) : prefs ? (
        <div>
          <Toggle
            checked={prefs.email_alerts_enabled}
            onChange={toggle("email_alerts_enabled")}
            label="Email alerts enabled"
            description="Master toggle — disabling this suppresses all alert emails."
          />
          <Toggle
            checked={prefs.alert_on_anomalies}
            onChange={toggle("alert_on_anomalies")}
            label="Revenue anomaly alerts"
            description="Email when daily revenue deviates more than 2.5σ from the mean."
          />
          <Toggle
            checked={prefs.alert_on_low_stock}
            onChange={toggle("alert_on_low_stock")}
            label="Low stock alerts"
            description="Email when any SKU falls below its reorder point."
          />
          {!prefs.email_alerts_enabled && (
            <p className="mt-3 text-xs text-muted-foreground italic">
              All email alerts are currently disabled. Toggle the master switch above to re-enable.
            </p>
          )}
        </div>
      ) : null}
    </SectionCard>
  );
}

function TeamSection({ currentUserId }: { currentUserId: string }) {
  const qc = useQueryClient();
  const [showInvite, setShowInvite] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => listUsersApi(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { role?: UserRole; is_active?: boolean } }) =>
      adminUpdateUserApi(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err.response?.data?.detail ?? "Update failed");
    },
  });

  const handleRoleChange = (id: string, role: UserRole) =>
    updateMutation.mutate({ id, payload: { role } });

  const handleToggleActive = (id: string, active: boolean) =>
    updateMutation.mutate({ id, payload: { is_active: active } });

  return (
    <SectionCard
      icon={Users}
      title={`Team Members${data ? ` · ${data.total}` : ""}`}
      action={
        <button
          onClick={() => setShowInvite((v) => !v)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 transition-colors"
        >
          {showInvite ? (
            <><X className="w-3.5 h-3.5" /> Cancel</>
          ) : (
            <><UserPlus className="w-3.5 h-3.5" /> Invite</>
          )}
        </button>
      }
    >
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin h-5 w-5 rounded-full border-2 border-brand-500 border-t-transparent" />
        </div>
      ) : (
        <div>
          {/* Column headers */}
          <div className="flex items-center gap-3 px-1 pb-2 border-b border-border">
            <div className="w-8 shrink-0" />
            <span className="flex-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">Member</span>
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide w-24 text-center">Role</span>
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide w-16 text-center">Status</span>
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide w-20 text-right hidden sm:block">Last Login</span>
          </div>

          {(data?.items ?? []).map((u) => (
            <UserRow
              key={u.id}
              user={u}
              isSelf={u.id === currentUserId}
              onRoleChange={handleRoleChange}
              onToggleActive={handleToggleActive}
            />
          ))}

          {data?.items.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-6">No team members yet.</p>
          )}
        </div>
      )}

      {showInvite && (
        <InviteForm
          onSuccess={() => {
            setShowInvite(false);
            qc.invalidateQueries({ queryKey: ["users"] });
          }}
        />
      )}
    </SectionCard>
  );
}

export function SettingsPage() {
  const { user, setUser } = useAuthStore();
  const { prefs, setDensity } = usePrefs();
  const [name, setName] = useState(user?.name ?? "");

  const isCeoOrAdmin = user?.role === "ceo" || user?.role === "admin";

  const mutation = useMutation({
    mutationFn: () => updateUserApi({ name }),
    onSuccess: (updated) => {
      setUser(updated);
      toast.success("Profile updated successfully");
    },
    onError: () => {
      toast.error("Failed to update profile");
    },
  });

  if (!user) return null;

  return (
    <div className="max-w-2xl mx-auto space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your profile and team.
        </p>
      </div>

      {/* Profile */}
      <SectionCard icon={User} title="Profile">
        <div className="space-y-4">
          <Field label="Display Name">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </Field>
          <Field label="Email">
            <input
              value={user.email}
              readOnly
              disabled
              className="h-9 w-full rounded-md border border-border bg-muted px-3 text-sm text-muted-foreground cursor-not-allowed"
            />
          </Field>
          <Field label="Role">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-3 py-1 text-xs font-medium capitalize border",
                  ROLE_COLORS[user.role as UserRole] ?? ROLE_COLORS.sales
                )}
              >
                {user.role}
              </span>
              {!isCeoOrAdmin && (
                <span className="text-xs text-muted-foreground">
                  Contact an admin to change your role.
                </span>
              )}
            </div>
          </Field>

          <div className="pt-2">
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending || name === user.name}
              className="inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Save className="w-4 h-4" />
              {mutation.isPending ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </div>
      </SectionCard>

      {/* Team Members — CEO/Admin only */}
      {isCeoOrAdmin && <TeamSection currentUserId={user.id} />}

      {/* Company — CEO/Admin only */}
      {isCeoOrAdmin && (
        <SectionCard icon={Building2} title="Company">
          <div className="space-y-4">
            <Field label="Company ID">
              <div className="h-9 flex items-center px-3 rounded-md border border-border bg-muted text-sm text-muted-foreground font-mono">
                {user.company_id}
              </div>
            </Field>
            <Field label="Plan">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center rounded-full bg-green-50 dark:bg-green-900/20 px-3 py-1 text-xs font-medium text-green-700 dark:text-green-400 capitalize border border-green-200 dark:border-green-800">
                  Free
                </span>
                <span className="text-xs text-muted-foreground">
                  100% free-tier infrastructure.
                </span>
              </div>
            </Field>
          </div>
        </SectionCard>
      )}

      {/* Email Alerts */}
      <EmailAlertsSection isCeoOrAdmin={isCeoOrAdmin} />

      {/* Appearance */}
      <SectionCard icon={Palette} title="Appearance">
        <div className="space-y-1">
          <Toggle
            checked={prefs.density === "compact"}
            onChange={(v) => setDensity(v ? "compact" : "comfortable")}
            label="Compact density"
            description="Reduces padding and font size by 25% for more data per screen."
          />
          <p className="pt-2 text-sm text-muted-foreground">
            Toggle dark mode using the{" "}
            <span className="font-medium text-foreground">sun/moon icon</span>{" "}
            in the top bar. Your preference is saved automatically.
          </p>
        </div>
      </SectionCard>

      {/* Account */}
      <SectionCard icon={Shield} title="Account">
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Member since</span>
            <span className="text-foreground font-medium">
              {new Date(user.created_at).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </span>
          </div>
          {user.last_login_at && (
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Last login</span>
              <span className="text-foreground font-medium">
                {new Date(user.last_login_at).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
            </div>
          )}
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Account status</span>
            <span className="text-green-600 font-medium">Active</span>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
