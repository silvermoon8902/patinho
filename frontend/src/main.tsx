import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "@/store";
import App from "@/App";
import { ToastProvider } from "@/components/shared/Toast";
import { ConfirmProvider } from "@/components/shared/ConfirmModal";
import "@/styles/globals.css";

// Sentry hook: activates only if VITE_SENTRY_DSN is set at build time.
// Loaded through window["Function"] to bypass TypeScript's static-import
// resolution — this keeps @sentry/react an optional dependency that only
// needs to be installed when the DSN is configured.
const sentryDsn = (import.meta as unknown as { env?: Record<string, string> })
  .env?.VITE_SENTRY_DSN;
if (sentryDsn) {
  const runtimeImport = new Function(
    "m",
    "return import(m)"
  ) as (m: string) => Promise<unknown>;
  runtimeImport("@sentry/react")
    .then((mod) => {
      const Sentry = mod as {
        init: (opts: Record<string, unknown>) => void;
      };
      Sentry.init({
        dsn: sentryDsn,
        environment: (import.meta as unknown as { env?: { MODE?: string } })
          .env?.MODE,
        tracesSampleRate: 0.05,
      });
      (window as unknown as { Sentry: typeof Sentry }).Sentry = Sentry;
    })
    .catch(() => {
      // @sentry/react not installed — skip silently.
    });
}

// Register the PWA service worker. Production-only so Vite dev HMR isn't
// interfered with. Fails silently if unsupported.
if (
  typeof window !== "undefined" &&
  "serviceWorker" in navigator &&
  (import.meta as unknown as { env?: { PROD?: boolean } }).env?.PROD
) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* swallow */
    });
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Provider store={store}>
      <BrowserRouter>
        <ToastProvider>
          <ConfirmProvider>
            <App />
          </ConfirmProvider>
        </ToastProvider>
      </BrowserRouter>
    </Provider>
  </React.StrictMode>
);
