import { useState, useEffect, useRef, FormEvent } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useNavigate, useSearchParams } from "react-router-dom";
import type { RootState, AppDispatch } from "@/store";
import apiClient from "@/api/client";
import {
  fetchWallet,
  createDeposit,
  fetchTransactions,
  clearDepositPayment,
  reconcileDeposit,
} from "@/store/walletSlice";
import { formatCurrency } from "@/utils/format";
import { useToast } from "@/components/shared/Toast";

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(dateStr));
}

const transactionTypeLabels: Record<string, string> = {
  deposit: "Depósito",
  withdrawal: "Saque",
  bet_lock: "Entrada no desafio",
  bet_unlock: "Desafio encerrado",
  prize_credit: "Prêmio recebido",
  fee_debit: "Taxa da plataforma",
  refund: "Reembolso",
};

// Negative types remove money from the user's available balance
const NEGATIVE_TYPES = new Set(["bet_lock", "fee_debit", "withdrawal"]);

export default function WalletPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { wallet, transactions, depositPayment, loading, error } = useSelector(
    (state: RootState) => state.wallet
  );

  const [depositAmount, setDepositAmount] = useState("");
  const [copied, setCopied] = useState(false);
  const [paymentMode, setPaymentMode] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const { showToast } = useToast();
  const pollRef = useRef<number | null>(null);
  const pollStartRef = useRef<number | null>(null);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // After a successful deposit, resume an interrupted journey (e.g. an
  // invite the user came from). Only accept absolute paths so external
  // open redirects can't piggyback on this param.
  const rawNext = searchParams.get("next") || "";
  const nextPath = rawNext.startsWith("/") ? rawNext : "";

  useEffect(() => {
    dispatch(fetchWallet());
    dispatch(fetchTransactions(1));
    apiClient
      .get("/wallet/payment-mode")
      .then((r) => setPaymentMode(r.data?.mode || null))
      .catch(() => setPaymentMode(null));
  }, [dispatch]);

  // Auto-poll reconcile every 5s while the Pix screen is up. Stops on
  // approval, on timeout (5 min), or when the user leaves / clears.
  useEffect(() => {
    const paymentId = depositPayment?.id;
    if (!paymentId) {
      if (pollRef.current != null) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
      pollStartRef.current = null;
      return;
    }
    pollStartRef.current = Date.now();
    const id = window.setInterval(async () => {
      const elapsed = Date.now() - (pollStartRef.current || Date.now());
      if (elapsed > 5 * 60 * 1000) {
        window.clearInterval(id);
        pollRef.current = null;
        return;
      }
      try {
        const action = await dispatch(reconcileDeposit(paymentId));
        if (reconcileDeposit.fulfilled.match(action)) {
          const balance = Number(action.payload?.balance ?? 0);
          const lastSeen = wallet?.balance;
          if (lastSeen !== undefined && balance > lastSeen) {
            showToast("Depósito confirmado!", "success");
            dispatch(clearDepositPayment());
            dispatch(fetchWallet());
            dispatch(fetchTransactions(1));
            window.clearInterval(id);
            pollRef.current = null;
            if (nextPath) navigate(nextPath, { replace: true });
          }
        }
      } catch {
        /* keep polling — reconcile is idempotent and best-effort */
      }
    }, 5000);
    pollRef.current = id;
    return () => {
      window.clearInterval(id);
      pollRef.current = null;
    };
  }, [depositPayment?.id, dispatch, showToast, wallet?.balance, nextPath, navigate]);

  const handleManualCheck = async () => {
    if (!depositPayment?.id || checking) return;
    setChecking(true);
    try {
      const action = await dispatch(reconcileDeposit(depositPayment.id));
      if (reconcileDeposit.fulfilled.match(action)) {
        const newBalance = Number(action.payload?.balance ?? 0);
        const oldBalance = Number(wallet?.balance ?? 0);
        if (newBalance > oldBalance) {
          showToast("Depósito confirmado!", "success");
          dispatch(clearDepositPayment());
          dispatch(fetchWallet());
          dispatch(fetchTransactions(1));
          if (nextPath) navigate(nextPath, { replace: true });
        } else {
          showToast("Ainda não recebido — tente novamente em alguns instantes.", "info");
        }
      } else {
        showToast("Não foi possível verificar agora.", "error");
      }
    } finally {
      setChecking(false);
    }
  };

  const handleDeposit = (e: FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(depositAmount);
    if (amount > 0) {
      dispatch(createDeposit(amount));
    }
  };

  const handleCopyPix = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = code;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="wallet-page">
      {/* Balance card */}
      <div className="card balance-card">
        <div className="balance-section">
          <span className="balance-label">Saldo disponível</span>
          <span className="balance-value">
            {wallet ? formatCurrency(wallet.balance) : "R$ 0,00"}
          </span>
        </div>
        <div className="balance-section balance-locked">
          <span className="balance-label">Saldo bloqueado</span>
          <span className="balance-value-small">
            {wallet ? formatCurrency(wallet.locked_balance) : "R$ 0,00"}
          </span>
        </div>
      </div>

      {/* Deposit section */}
      <div className="card">
        <h3>Depositar</h3>
        {paymentMode === "test" && (
          <div className="payment-mode-badge">
            Modo de teste — nenhuma transação real ocorre
          </div>
        )}
        {paymentMode === "simulated" && (
          <div className="payment-mode-badge">
            Modo simulado — depósitos são creditados automaticamente em ~5s, sem Pix real
          </div>
        )}
        {paymentMode === "unconfigured" && (
          <div className="payment-mode-badge">
            Pagamentos ainda não configurados — depósitos indisponíveis
          </div>
        )}
        {!depositPayment ? (
          <form className="deposit-form" onSubmit={handleDeposit}>
            <div className="form-group">
              <label htmlFor="depositAmount">Valor (R$)</label>
              <input
                id="depositAmount"
                type="number"
                min="1"
                step="0.01"
                placeholder="0,00"
                value={depositAmount}
                onChange={(e) => setDepositAmount(e.target.value)}
                required
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary btn-full"
              disabled={loading}
            >
              {loading ? "Gerando Pix..." : "Depositar via Pix"}
            </button>
          </form>
        ) : (
          <div className="pix-payment">
            <p className="pix-instruction">
              Escaneie o QR Code ou copie o código Pix abaixo:
            </p>
            {depositPayment.pix_qr_code && (
              <div className="pix-qr">
                <img
                  src={`data:image/png;base64,${depositPayment.pix_qr_code}`}
                  alt="QR Code Pix"
                  className="qr-image"
                />
              </div>
            )}
            <div className="pix-code-container">
              <code className="pix-code">{depositPayment.pix_copy_paste}</code>
              <button
                className="btn btn-secondary btn-copy"
                onClick={() => handleCopyPix(depositPayment.pix_copy_paste || "")}
              >
                {copied ? "Copiado!" : "Copiar"}
              </button>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-full"
              onClick={handleManualCheck}
              disabled={checking}
              style={{ marginBottom: "8px" }}
            >
              {checking ? "Verificando..." : "Já paguei — verificar agora"}
            </button>
            <p className="form-hint" style={{ textAlign: "center", marginBottom: "8px" }}>
              Estamos conferindo automaticamente a cada 5 segundos.
            </p>
            <button
              className="btn btn-secondary btn-full"
              onClick={() => {
                dispatch(clearDepositPayment());
                setDepositAmount("");
                dispatch(fetchWallet());
              }}
            >
              Cancelar e fazer outro depósito
            </button>
          </div>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Transaction history */}
      <div className="card">
        <h3>Extrato</h3>
        {transactions.length === 0 ? (
          <p className="empty-state">Nenhuma transação encontrada</p>
        ) : (
          <ul className="transaction-list">
            {transactions.map((tx) => {
              const isNegative = NEGATIVE_TYPES.has(tx.type);
              const amount = Math.abs(Number(tx.amount));
              return (
                <li key={tx.id} className="transaction-item">
                  <div className="transaction-info">
                    <span className="transaction-type">
                      {transactionTypeLabels[tx.type] || tx.type}
                    </span>
                    <span className="transaction-date">
                      {formatDate(tx.created_at)}
                    </span>
                  </div>
                  <span
                    className={`transaction-amount ${isNegative ? "negative" : "positive"}`}
                  >
                    {isNegative ? "-" : "+"}
                    {formatCurrency(amount)}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
