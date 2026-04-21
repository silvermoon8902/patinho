import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { fetchBetByInvite, joinBet, clearBetError } from "@/store/betSlice";
import { formatCurrency } from "@/utils/format";
import apiClient from "@/api/client";

const CATEGORY_LABELS: Record<string, string> = {
  football: "Futebol",
  f1: "F1",
  tennis: "Tênis",
  bbb: "BBB",
  politics: "Política",
  custom: "Outro",
};

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString("pt-BR");
}

interface PixPayment {
  id: string;
  amount: number | string;
  status: string;
  pix_qr_code: string | null;
  pix_copy_paste: string | null;
  expires_at: string;
}

export default function InvitePage() {
  const { inviteToken } = useParams<{ inviteToken: string }>();
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();

  const { currentBet, loading, error } = useSelector(
    (state: RootState) => state.bets
  );
  const { accessToken, user } = useSelector((state: RootState) => state.auth);
  const isAuthenticated = !!accessToken;

  const [selectedOption, setSelectedOption] = useState("");
  const [pixPayment, setPixPayment] = useState<PixPayment | null>(null);
  const [pixCopied, setPixCopied] = useState(false);
  const [pixError, setPixError] = useState<string | null>(null);
  const [pixLoading, setPixLoading] = useState(false);

  useEffect(() => {
    if (inviteToken) {
      dispatch(fetchBetByInvite(inviteToken));
    }
    return () => {
      dispatch(clearBetError());
    };
  }, [dispatch, inviteToken]);

  const handleRegisterRedirect = () => {
    navigate(`/register?redirect=/invite/${inviteToken}`);
  };

  const handleLoginRedirect = () => {
    navigate(`/login?redirect=/invite/${inviteToken}`);
  };

  const handleJoinWithBalance = async () => {
    if (!currentBet || !selectedOption) return;
    const result = await dispatch(
      joinBet({ betId: currentBet.id, optionId: selectedOption })
    );
    if (joinBet.fulfilled.match(result)) {
      navigate(`/bets/${currentBet.id}`);
    }
  };

  const handleDirectJoinPix = async () => {
    if (!currentBet || !selectedOption) return;
    setPixError(null);
    setPixLoading(true);
    try {
      const response = await apiClient.post(
        `/bets/${currentBet.id}/direct-join`,
        {
          bet_option_id: selectedOption,
          amount: currentBet.entry_amount,
        }
      );
      setPixPayment(response.data);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setPixError(e.response?.data?.detail || "Erro ao gerar Pix");
    } finally {
      setPixLoading(false);
    }
  };

  const handleCopyPix = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setPixCopied(true);
      setTimeout(() => setPixCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = code;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setPixCopied(true);
      setTimeout(() => setPixCopied(false), 2000);
    }
  };

  if (loading && !currentBet) {
    return (
      <div className="invite-page">
        <div className="invite-container">
          <div className="bets-loading">Carregando convite...</div>
        </div>
      </div>
    );
  }

  if (!currentBet) {
    return (
      <div className="invite-page">
        <div className="invite-container">
          <div className="invite-card card">
            <h2>Convite não encontrado</h2>
            <p className="invite-error-text">
              Este link de convite é inválido ou o desafio não existe mais.
            </p>
            <button
              className="btn btn-primary btn-full"
              onClick={() => navigate("/")}
            >
              Ir para o início
            </button>
          </div>
        </div>
      </div>
    );
  }

  const userAlreadyJoined = (currentBet.participations || []).some(
    (p) => p.user_id === user?.id
  );

  return (
    <div className="invite-page">
      <div className="invite-container">
        <div className="invite-brand">
          <h2 className="invite-brand-title">Patinho</h2>
          <p className="invite-brand-sub">Você foi convidado para um desafio</p>
        </div>

        {/* Bet preview card */}
        <div className="invite-card card">
          <div className="bet-hero-header">
            <span className={`category-tag category-${currentBet.category}`}>
              {CATEGORY_LABELS[currentBet.category] || currentBet.category}
            </span>
          </div>
          <h2 className="invite-bet-title">{currentBet.title}</h2>
          {currentBet.description && (
            <p className="invite-bet-desc">{currentBet.description}</p>
          )}

          <div className="invite-details">
            <div className="invite-detail-row">
              <span className="invite-detail-label">Opções</span>
              <div className="invite-options-list">
                {(currentBet.options || []).map((opt) => (
                  <span key={opt.id} className="review-option-tag">
                    {opt.label}
                  </span>
                ))}
              </div>
            </div>
            <div className="invite-detail-row">
              <span className="invite-detail-label">Participantes</span>
              <span className="invite-detail-value">
                {currentBet.current_participants}
              </span>
            </div>
            <div className="invite-detail-row">
              <span className="invite-detail-label">Pote atual</span>
              <span className="invite-detail-value">
                {formatCurrency((currentBet.participations || []).reduce((sum, p) => sum + p.amount, 0))}
              </span>
            </div>
            <div className="invite-detail-row">
              <span className="invite-detail-label">Entrada</span>
              <span className="invite-detail-value">
                {formatCurrency(currentBet.entry_amount)}
              </span>
            </div>
            <div className="invite-detail-row">
              <span className="invite-detail-label">Encerramento</span>
              <span className="invite-detail-value">
                {formatDate(currentBet.closes_at)}
              </span>
            </div>
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {pixError && <div className="alert alert-error">{pixError}</div>}

        {/* Action section */}
        {!isAuthenticated ? (
          <div className="invite-action card">
            <p className="invite-action-text">
              Para participar deste desafio, crie sua conta ou faça login.
            </p>
            <button
              className="btn btn-primary btn-full"
              onClick={handleRegisterRedirect}
            >
              Criar conta
            </button>
            <button
              className="btn btn-secondary btn-full"
              style={{ marginTop: "8px" }}
              onClick={handleLoginRedirect}
            >
              Já tenho conta
            </button>
          </div>
        ) : userAlreadyJoined ? (
          <div className="invite-action card">
            <p className="invite-action-text">
              Você já está participando deste desafio.
            </p>
            <button
              className="btn btn-primary btn-full"
              onClick={() => navigate(`/bets/${currentBet.id}`)}
            >
              Ver desafio
            </button>
          </div>
        ) : currentBet.status !== "open" ? (
          <div className="invite-action card">
            <p className="invite-action-text">
              Este desafio não está mais aceitando participantes.
            </p>
          </div>
        ) : pixPayment ? (
          <div className="invite-action card">
            <h3>Pague para participar</h3>
            <p className="pix-instruction">
              Escaneie o QR Code ou copie o código Pix. Após o pagamento você entra automaticamente no desafio.
            </p>
            {pixPayment.pix_qr_code && (
              <div className="pix-qr">
                <img
                  src={`data:image/png;base64,${pixPayment.pix_qr_code}`}
                  alt="QR Code Pix"
                  className="qr-image"
                />
              </div>
            )}
            {pixPayment.pix_copy_paste && (
              <div className="pix-code-container">
                <code className="pix-code">{pixPayment.pix_copy_paste}</code>
                <button
                  className="btn btn-secondary btn-copy"
                  onClick={() => handleCopyPix(pixPayment.pix_copy_paste!)}
                >
                  {pixCopied ? "Copiado!" : "Copiar"}
                </button>
              </div>
            )}
            <button
              className="btn btn-secondary btn-full"
              style={{ marginTop: "12px" }}
              onClick={() => setPixPayment(null)}
            >
              Cancelar
            </button>
          </div>
        ) : (
          <div className="invite-action card">
            <h3>Participar do desafio</h3>
            <div className="bet-join-amount">
              <span className="bet-join-amount-label">Valor:</span>
              <span className="bet-join-amount-value">
                {formatCurrency(currentBet.entry_amount)}
              </span>
            </div>
            <div className="form-group">
              <label>Escolha uma opção</label>
              <select
                className="form-select"
                value={selectedOption}
                onChange={(e) => setSelectedOption(e.target.value)}
              >
                <option value="">Selecione...</option>
                {(currentBet.options || []).map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <button
              className="btn btn-primary btn-full"
              onClick={handleJoinWithBalance}
              disabled={!selectedOption || loading}
            >
              {loading
                ? "Entrando..."
                : `Usar saldo: ${formatCurrency(currentBet.entry_amount)}`}
            </button>
            <button
              className="btn btn-secondary btn-full"
              style={{ marginTop: "8px" }}
              onClick={handleDirectJoinPix}
              disabled={!selectedOption || pixLoading}
            >
              {pixLoading ? "Gerando Pix..." : "Pagar via Pix e participar"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
