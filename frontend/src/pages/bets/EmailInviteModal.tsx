import { useEffect, useState } from "react";
import apiClient from "@/api/client";
import { useToast } from "@/components/shared/Toast";

interface Props {
  open: boolean;
  betId: string;
  onClose: () => void;
}

type InviteStatus = "sent" | "failed" | "skipped" | "not_in_league";

interface EmailResult {
  email: string;
  status: InviteStatus;
}

const MAX_EMAILS = 10;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function EmailInviteModal({ open, betId, onClose }: Props) {
  const { showToast } = useToast();
  const [raw, setRaw] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<EmailResult[] | null>(null);

  useEffect(() => {
    if (!open) {
      setRaw("");
      setResults(null);
      setLoading(false);
    }
  }, [open]);

  if (!open) return null;

  const parseEmails = (): string[] => {
    return raw
      .split(/[\s,;]+/)
      .map((e) => e.trim())
      .filter((e) => e.length > 0);
  };

  const emails = parseEmails();
  const invalid = emails.filter((e) => !EMAIL_RE.test(e));
  const tooMany = emails.length > MAX_EMAILS;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (emails.length === 0) {
      showToast("Digite pelo menos um email", "error");
      return;
    }
    if (invalid.length > 0) {
      showToast(`Email(s) inválido(s): ${invalid.join(", ")}`, "error");
      return;
    }
    if (tooMany) {
      showToast(`Máximo de ${MAX_EMAILS} emails por vez`, "error");
      return;
    }
    setLoading(true);
    try {
      const response = await apiClient.post(`/bets/${betId}/email-invite`, {
        emails,
      });
      const data = response.data as { results: Record<string, InviteStatus> };
      const list: EmailResult[] = Object.entries(data.results || {}).map(
        ([email, status]) => ({ email, status })
      );
      setResults(list);
      const sent = list.filter((r) => r.status === "sent").length;
      if (sent > 0) {
        showToast(
          sent === 1 ? "1 convite enviado" : `${sent} convites enviados`,
          "success"
        );
      } else {
        showToast("Nenhum convite foi enviado", "info");
      }
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } };
      showToast(
        e.response?.data?.detail || "Erro ao enviar convites",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="league-modal-overlay"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="card league-modal-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Convidar por email</h2>
        <p className="league-modal-subtitle">
          Separe com vírgula, ponto-e-vírgula ou uma por linha. Máximo{" "}
          {MAX_EMAILS} endereços por envio.
        </p>

        <form onSubmit={handleSubmit} className="league-form">
          <div className="form-group">
            <label htmlFor="invite-emails">Emails</label>
            <textarea
              id="invite-emails"
              className="form-input"
              rows={4}
              required
              autoFocus
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              placeholder="amigo1@email.com, amigo2@email.com"
              disabled={loading}
            />
            {emails.length > 0 && (
              <span className="form-hint">
                {emails.length} endereço{emails.length !== 1 ? "s" : ""}
                {invalid.length > 0 &&
                  ` — ${invalid.length} inválido${
                    invalid.length !== 1 ? "s" : ""
                  }`}
                {tooMany && ` — passou do limite de ${MAX_EMAILS}`}
              </span>
            )}
          </div>

          {results && results.length > 0 && (
            <div className="email-invite-results">
              {results.map((r) => (
                <div
                  key={r.email}
                  className={`alert alert-${
                    r.status === "sent"
                      ? "success"
                      : r.status === "skipped" || r.status === "not_in_league"
                      ? "info"
                      : "error"
                  }`}
                >
                  <strong>{r.email}</strong> —{" "}
                  {r.status === "sent"
                    ? "enviado"
                    : r.status === "skipped"
                    ? "já participa do desafio"
                    : r.status === "not_in_league"
                    ? "adicione essa pessoa à liga primeiro"
                    : "falhou"}
                </div>
              ))}
            </div>
          )}

          <div className="league-modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Fechar
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || emails.length === 0 || invalid.length > 0 || tooMany}
            >
              {loading ? "Enviando..." : "Enviar convites"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
