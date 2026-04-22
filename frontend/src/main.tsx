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
// Import is dynamic so the @sentry/react dependency is optional —
// developers without it still get a functional build.
const sentryDsn = import.meta.env.VITE_SENTRY_DSN as string | undefined;
if (sentryDsn) {
  import("@sentry/react")
    .then((Sentry) => {
      Sentry.init({
        dsn: sentryDsn,
        environment: import.meta.env.MODE,
        tracesSampleRate: 0.05,
        replaysSessionSampleRate: 0,
        replaysOnErrorSampleRate: 0.1,
      });
      (window as unknown as { Sentry: typeof Sentry }).Sentry = Sentry;
    })
    .catch(() => {
      // @sentry/react not installed locally — skip silently.
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
