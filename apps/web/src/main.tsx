import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { Toaster } from "sonner";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { PrefsProvider } from "./state/PrefsContext";
import { router } from "./app/router";
import { queryClient } from "./lib/queryClient";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <PrefsProvider>
          <RouterProvider router={router} />
          <Toaster
            position="top-right"
            richColors
            closeButton
            toastOptions={{ duration: 4000 }}
          />
          {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
        </PrefsProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
