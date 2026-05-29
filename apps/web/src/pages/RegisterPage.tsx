import { useState } from "react";
import { Navigate, Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useAuthStore } from "@/features/auth/authStore";
import { registerApi } from "@/features/auth/api";

const schema = z
  .object({
    company_name: z.string().min(2, "Company name must be at least 2 characters"),
    name: z.string().min(1, "Your name is required"),
    email: z.string().email("Enter a valid email"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string(),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

const inputCls =
  "w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand-600/40 focus:border-brand-600 transition";

export function RegisterPage() {
  const { isAuthenticated, setAuth } = useAuthStore();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  async function onSubmit(values: FormValues) {
    setLoading(true);
    try {
      const { access_token, user } = await registerApi({
        company_name: values.company_name,
        email: values.email,
        password: values.password,
        name: values.name,
      });
      setAuth(user, access_token);
      toast.success(`Welcome to RetailFlux, ${user.name}!`);
      navigate("/dashboard", { replace: true });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : "Registration failed. Please try again.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background py-8">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-brand-600 flex items-center justify-center mb-4">
            <span className="text-white text-lg font-bold">RF</span>
          </div>
          <h1 className="text-2xl font-semibold text-foreground">RetailFlux</h1>
          <p className="text-sm text-muted-foreground mt-1">Fashion Analytics Intelligence</p>
        </div>

        {/* Card */}
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-foreground mb-1">Create your account</h2>
          <p className="text-sm text-muted-foreground mb-6">
            You'll be the CEO — invite your team later.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Company name
              </label>
              <input {...register("company_name")} type="text" placeholder="ACME Fashion Ltd" className={inputCls} />
              {errors.company_name && (
                <p className="mt-1 text-xs text-danger">{errors.company_name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Your full name
              </label>
              <input {...register("name")} type="text" placeholder="Jane Smith" className={inputCls} />
              {errors.name && (
                <p className="mt-1 text-xs text-danger">{errors.name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Work email
              </label>
              <input
                {...register("email")}
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                className={inputCls}
              />
              {errors.email && (
                <p className="mt-1 text-xs text-danger">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Password
              </label>
              <input
                {...register("password")}
                type="password"
                autoComplete="new-password"
                placeholder="Min. 8 characters"
                className={inputCls}
              />
              {errors.password && (
                <p className="mt-1 text-xs text-danger">{errors.password.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Confirm password
              </label>
              <input
                {...register("confirm_password")}
                type="password"
                autoComplete="new-password"
                placeholder="Repeat password"
                className={inputCls}
              />
              {errors.confirm_password && (
                <p className="mt-1 text-xs text-danger">{errors.confirm_password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
            >
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p className="text-xs text-center text-muted-foreground mt-4">
            Already have an account?{" "}
            <Link to="/login" className="text-brand-600 hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
