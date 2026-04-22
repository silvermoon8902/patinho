import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

type ConfirmTone = "default" | "danger" | "warning";

interface ConfirmOptions {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: ConfirmTone;
}

type ConfirmFn = (opts: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmFn | null>(null);

export function useConfirm(): ConfirmFn {
  const ctx = useContext(ConfirmContext);
  if (!ctx) {
    throw new Error("useConfirm must be used inside <ConfirmProvider>");
  }
  return ctx;
}

interface PendingConfirm extends ConfirmOptions {
  resolve: (value: boolean) => void;
}

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [pending, setPending] = useState<PendingConfirm | null>(null);
  const confirmBtnRef = useRef<HTMLButtonElement | null>(null);

  const confirm = useCallback<ConfirmFn>((opts) => {
    return new Promise<boolean>((resolve) => {
      setPending({ ...opts, resolve });
    });
  }, []);

  const close = useCallback((value: boolean) => {
    setPending((prev) => {
      if (prev) prev.resolve(value);
      return null;
    });
  }, []);

  // Focus the confirm button when modal opens
  useEffect(() => {
    if (pending) {
      const t = setTimeout(() => {
        confirmBtnRef.current?.focus();
      }, 20);
      return () => clearTimeout(t);
    }
  }, [pending]);

  // Close on Escape; submit on Enter
  useEffect(() => {
    if (!pending) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close(false);
      } else if (e.key === "Enter") {
        e.preventDefault();
        close(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pending, close]);

  // Lock body scroll while open
  useEffect(() => {
    if (!pending) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [pending]);

  const tone: ConfirmTone = pending?.tone || "default";
  const confirmClass = useMemo(() => {
    if (tone === "danger") return "btn btn-danger";
    if (tone === "warning") return "btn btn-warning";
    return "btn btn-primary";
  }, [tone]);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {pending && (
        <div
          className="confirm-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
          onClick={() => close(false)}
        >
          <div
            className={`confirm-card confirm-tone-${tone}`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={`confirm-icon confirm-icon-${tone}`} aria-hidden="true">
              {tone === "danger" ? "!" : tone === "warning" ? "!" : "?"}
            </div>
            <h2 id="confirm-title" className="confirm-title">
              {pending.title}
            </h2>
            {pending.message && (
              <p className="confirm-message">{pending.message}</p>
            )}
            <div className="confirm-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => close(false)}
              >
                {pending.cancelLabel || "Cancelar"}
              </button>
              <button
                ref={confirmBtnRef}
                type="button"
                className={confirmClass}
                onClick={() => close(true)}
              >
                {pending.confirmLabel || "Confirmar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}
