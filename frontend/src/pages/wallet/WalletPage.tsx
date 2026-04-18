import { useState, useEffect, FormEvent } from "react";
import { useSelector, useDispatch } from "react-redux";
import type { RootState, AppDispatch } from "@/store";
import {
  fetchWallet,
  createDeposit,
  fetchTransactions,
  clearDepositPayment,
} from "@/store/walletSlice";
import { formatCurrency } from "@/utils/format";

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
  deposit: "Deposito",
  withdrawal: "Saque",
  bet_placed: "Entrada no desafio",
  bet_won: "Desafio ganho",
  bet_refund: "Reembolso",
};

export default function WalletPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { wallet, transactions, depositPayment, loading, error } = useSelector(
    (state: RootState) => state.wallet
  );

  const [depositAmount, setDepositAmount] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    dispatch(fetchWallet());
    dispatch(fetchTransactions(1));
  }, [dispatch]);

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
          <span className="balance-label">Saldo disponivel</span>
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
              Escaneie o QR Code ou copie o codigo Pix abaixo:
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
              className="btn btn-secondary btn-full"
              onClick={() => {
                dispatch(clearDepositPayment());
                setDepositAmount("");
                dispatch(fetchWallet());
              }}
            >
              Fazer outro deposito
            </button>
          </div>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Transaction history */}
      <div className="card">
        <h3>Extrato</h3>
        {transactions.length === 0 ? (
          <p className="empty-state">Nenhuma transacao encontrada</p>
        ) : (
          <ul className="transaction-list">
            {transactions.map((tx) => (
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
                  className={`transaction-amount ${
                    tx.amount >= 0 ? "positive" : "negative"
                  }`}
                >
                  {tx.amount >= 0 ? "+" : ""}
                  {formatCurrency(tx.amount)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
