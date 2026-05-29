import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // RetailFlux brand accent — indigo
        brand: {
          "50": "#eef2ff",
          "100": "#e0e7ff",
          "200": "#c7d2fe",
          "300": "#a5b4fc",
          "400": "#818cf8",
          "500": "#6366f1",
          "600": "#4f46e5",
          "700": "#4338ca",
          "800": "#3730a3",
          "900": "#312e81",
        },
        // Surface elevation scale
        surface: {
          "1": "hsl(var(--surface-1))",
          "2": "hsl(var(--surface-2))",
          "3": "hsl(var(--surface-3))",
          overlay: "hsl(var(--surface-overlay))",
        },
        // Semantic status — CSS variable driven
        ok:   { DEFAULT: "hsl(var(--ok))" },
        warn: { DEFAULT: "hsl(var(--warn))" },
        bad:  { DEFAULT: "hsl(var(--bad))" },
        info: { DEFAULT: "hsl(var(--info))" },
        ai:   {
          DEFAULT: "hsl(var(--ai))",
          from: "hsl(var(--ai-from))",
          to:   "hsl(var(--ai-to))",
        },
        // Legacy aliases kept for backward compat
        success: { DEFAULT: "#22c55e", light: "#dcfce7" },
        warning: { DEFAULT: "#f59e0b", light: "#fef3c7" },
        danger:  { DEFAULT: "#ef4444", light: "#fee2e2" },
      },

      // ── 7-step type scale ───────────────────────────────────────────────── //
      fontSize: {
        // [font-size, { lineHeight, letterSpacing, fontWeight }]
        display: ["2.5rem",   { lineHeight: "1.1",  letterSpacing: "-0.03em" }],
        h1:      ["2rem",     { lineHeight: "1.15", letterSpacing: "-0.025em" }],
        h2:      ["1.5rem",   { lineHeight: "1.2",  letterSpacing: "-0.02em" }],
        section: ["1.125rem", { lineHeight: "1.35", letterSpacing: "-0.01em" }],
        body:    ["0.875rem", { lineHeight: "1.5",  letterSpacing: "0" }],
        caption: ["0.75rem",  { lineHeight: "1.4",  letterSpacing: "0.005em" }],
        micro:   ["0.6875rem",{ lineHeight: "1.4",  letterSpacing: "0.01em" }],
      },

      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },

      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "sans-serif",
          {
            fontFeatureSettings: '"ss01", "cv11", "tnum"',
            fontVariantNumeric: "tabular-nums",
          },
        ],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },

      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "fade-out": { from: { opacity: "1" }, to: { opacity: "0" } },
        "slide-in": {
          from: { transform: "translateX(-100%)" },
          to: { transform: "translateX(0)" },
        },
        "slide-in-right": {
          from: { transform: "translateX(100%)" },
          to:   { transform: "translateX(0)" },
        },
        "slide-up": {
          from: { transform: "translateY(100%)" },
          to:   { transform: "translateY(0)" },
        },
        "scale-in": {
          from: { transform: "scale(0.95)", opacity: "0" },
          to:   { transform: "scale(1)",    opacity: "1" },
        },
      },

      animation: {
        "fade-in":        "fade-in 0.15s ease-out",
        "fade-out":       "fade-out 0.15s ease-in",
        "slide-in":       "slide-in 0.2s ease-out",
        "slide-in-right": "slide-in-right 0.2s ease-out",
        "slide-up":       "slide-up 0.25s ease-out",
        "scale-in":       "scale-in 0.12s ease-out",
      },

      transitionTimingFunction: {
        emphasized: "cubic-bezier(0.2, 0, 0, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
