import React from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Copy, Home, RefreshCw } from "lucide-react";
import { toast } from "sonner";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  traceId: string;
}

function generateTraceId(): string {
  return (
    Math.random().toString(36).slice(2, 7) + "-" + Date.now().toString(36).slice(-4)
  ).toUpperCase();
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, traceId: generateTraceId() };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error, traceId: generateTraceId() };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", { error, componentStack: info.componentStack, traceId: this.state.traceId });
  }

  private handleCopyTrace = () => {
    void navigator.clipboard.writeText(
      `Trace ID: ${this.state.traceId}\nError: ${this.state.error?.message ?? "Unknown"}`
    );
    toast.success("Trace ID copied to clipboard");
  };

  private handleReport = () => {
    console.error("[ErrorReport]", {
      traceId: this.state.traceId,
      error: this.state.error?.message,
      stack: this.state.error?.stack,
    });
    toast.info("Error reported. Thank you for helping us improve RetailFlux.");
  };

  private handleRetry = () => {
    this.setState({ hasError: false, error: null, traceId: generateTraceId() });
  };

  render() {
    if (this.props.fallback && this.state.hasError) return this.props.fallback;

    if (this.state.hasError) {
      const { error, traceId } = this.state;
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-5 p-8 text-center">
          <div className="rounded-full bg-red-100 dark:bg-red-900/30 p-4">
            <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
          </div>

          <div className="space-y-1.5 max-w-md">
            <h2 className="text-lg font-semibold text-foreground">Something went wrong</h2>
            <p className="text-sm text-muted-foreground">
              {error?.message ?? "An unexpected error occurred in this part of the page."}
            </p>
          </div>

          {/* Trace ID chip */}
          <div className="flex items-center gap-2 bg-muted/50 border border-border rounded-md px-3 py-1.5">
            <span className="text-xs text-muted-foreground font-mono">Trace&nbsp;ID:</span>
            <code className="text-xs font-mono text-foreground">{traceId}</code>
            <button
              onClick={this.handleCopyTrace}
              className="text-muted-foreground hover:text-foreground transition-colors"
              title="Copy trace ID"
              aria-label="Copy trace ID"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap items-center justify-center gap-2 mt-1">
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-background outline-none"
            >
              <RefreshCw className="w-4 h-4" />
              Try again
            </button>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-4 py-2 border border-border rounded-md text-sm font-medium hover:bg-accent transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-background outline-none"
            >
              <Home className="w-4 h-4" />
              Go to Master Dashboard
            </Link>
            <button
              onClick={this.handleReport}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-background outline-none rounded-md"
            >
              Report this
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
