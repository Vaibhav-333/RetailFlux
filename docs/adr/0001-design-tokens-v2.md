# ADR-0001: Design Tokens v2 — Surface Elevation Scale + AI Gradient

**Date:** 2026-05-25
**Status:** Accepted

---

## Context

RetailFlux v2 shipped with a single `--card` CSS custom property as its only surface color, creating a flat, undifferentiated dark UI. Enterprise dashboards (Bloomberg, Linear, Notion) achieve "premium" depth through layered surfaces — subtly lighter backgrounds at higher elevations — without relying on blur effects that degrade performance on lower-end hardware.

Additionally, AI-generated content (insights, copilot answers, forecasted values) was visually indistinguishable from user-authored or real-time data. This created a trust problem: users had no visual signal indicating when they were looking at a model output vs. a database fact.

Two concerns drove the redesign:
1. **Depth without blur** — 4 surface levels (`--surface-1` through `--surface-3` + `--overlay`) using incrementally lighter fills + a 1px inset highlight (`box-shadow: inset 0 1px 0 hsl(0 0% 100% / 0.04)`).
2. **AI visual language** — a dedicated `--ai` gradient token (violet → cyan) reserved exclusively for AI-generated content surfaces, borders, and badges.

---

## Decision

Adopt an **additive CSS variable expansion** in `src/index.css` and `tailwind.config.ts`, layered on top of the existing token set without breaking any existing component.

The full token set added:
- **Surface elevation:** `--surface-1 / --surface-2 / --surface-3 / --overlay`
- **Glow accent:** `--brand-glow: 0 0 24px hsl(239 84% 67% / 0.35)` — used on focused KPI cards and the AI panel header
- **Semantic states:** `--ok / --warn / --bad / --info / --ai`
- **Motion:** `--ease-emphasized: cubic-bezier(0.2, 0, 0, 1)`, `--dur-1: 120ms`, `--dur-2: 200ms`, `--dur-3: 320ms`
- **Type scale:** 7 steps (Display → Micro) with `font-feature-settings: "ss01", "cv11", "tnum"` for Inter ligatures + tabular numerals
- **Density modes:** `density-comfortable` (default) and `density-compact` (-25% padding, -1 type step), toggled in Settings and persisted in `users.prefs` JSONB

---

## Alternatives Considered

### Tailwind v4 full migration
Tailwind v4 ships with a new design token system natively. Migrating would give us the most future-proof foundation. **Rejected** because v4 was still in beta at implementation time and would have required rewriting all 25 pages' className strings — too disruptive to ship within session scope.

### shadcn/ui theming only
shadcn exposes `--background`, `--card`, `--muted` etc. as theme variables. Extending only within that system would have constrained us to its opinionated structure. **Rejected** because RetailFlux needs a `--ai` gradient that has no shadcn analogue and the density system is orthogonal to shadcn's concerns.

### Separate design token file (JSON / style-dictionary)
Using Style Dictionary to generate tokens from a JSON source would enable multi-platform parity (native mobile, email templates). **Rejected** as out-of-scope for v3; a `src/design/tokens.ts` TypeScript export provides the same compile-time guarantees with zero additional tooling.

---

## Consequences

**Positive:**
- Zero breaking changes — all existing components continue using `--card` unchanged; elevation tokens are opt-in.
- `--ai` gradient creates an immediately legible visual contract: if you see violet-cyan, it's AI-generated.
- Density compact mode targets power users who want Bloomberg-style information density without a separate product SKU.
- Motion tokens prevent ad-hoc animation durations scattered across the codebase.

**Negative / Trade-offs:**
- Two density modes double the QA surface for layout testing (every page must be verified at both densities).
- `--ai` token must be enforced by convention, not the type system — a future design system linter rule is recommended.
- Adding 7 type scale steps increases the number of classes to remember; the Storybook component library mitigates this.

**Follow-ons:**
- v3.x: migrate `--card` usages progressively to the elevation scale.
- v3.x: add `prefers-contrast: more` media query variant for accessibility.
- v3.x: Tailwind v4 migration when stable.
