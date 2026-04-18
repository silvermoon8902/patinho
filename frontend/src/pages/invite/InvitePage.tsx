import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { fetchBetByInvite, joinBet, clearBetError } from "@/store/betSlice";

const CATEGORY_LABELS: Record<string, string> = {
  football: "Futebol",
  f1: "F1",
  tennis: "Tenis",
  bbb: "BBB",
  politics: "Politica",
  custom: "Outro",
};

function formatCurrency(value: number): string {
  return `R$ ${value.toFixed(2).replace(".", ",")}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString("pt-BR");
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

  useEffect(() => {
    if (inviteToken) {
      dispatch(fetchBetByInvite(inviteToken));
    }
    return () => {
      dispatch(clearBetError());
    };
  }, [dispatch, inviteToken]);

  const handleLoginRedirect = () => {
    navigate(`/register?redirect=/invite/${inviteToken}`);
  };

  const handleJoin = async () => {
    if (!currentBet || !selectedOption) return;
    const result = await dispatch(
      joinBet({ betId: currentBet.id, optionId: selectedOption })
    );
    if (joinBet.fulfilled.match(result)) {
      navigate(`/bets/${currentBet.id}`);
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
            <h2>Convite nao encontrado</h2>
            <p className="invite-error-text">
              Este link de convite e invalido ou o desafio nao existe mais.
            </p>
            <button
              className="btn btn-primary btn-full"
              onClick={() => navigate("/")}
            >
              Ir para o inicio
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
          <p className="invite-brand-sub">Voce foi convidado para um desafio</p>
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
              <span className="invite-detail-label">Opcoes</span>
              <div className="invite-options-list">
                {currentBet.options.map((opt) => (
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

        {/* Action section */}
        {!isAuthenticated ? (
          <div className="invite-action card">
            <p className="invite-action-text">
              Para participar deste desafio, crie sua conta ou faca login.
            </p>
            <button
              className="btn btn-primary btn-full"
              onClick={handleLoginRedirect}
            >
              Entrar e participar
            </button>
          </div>
        ) : userAlreadyJoined ? (
          <div className="invite-action card">
            <p className="invite-action-text">
              Voce ja esta participando deste desafio.
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
              Este desafio nao esta mais aceitando participantes.
            </p>
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
              <label>Escolha uma opcao</label>
              <select
                className="form-select"
                value={selectedOption}
                onChange={(e) => setSelectedOption(e.target.value)}
              >
                <option value="">Selecione...</option>
                {currentBet.options.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <button
              className="btn btn-primary btn-full"
              onClick={handleJoin}
              disabled={!selectedOption || loading}
            >
              {loading
                ? "Entrando..."
                : `Participar por ${formatCurrency(currentBet.entry_amount)}`}
            </button>
            <button
              className="btn btn-secondary btn-full"
              style={{ marginTop: "8px" }}
              onClick={handleJoin}
              disabled={!selectedOption || loading}
            >
              Pagar via Pix e participar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
