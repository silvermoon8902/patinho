import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { fetchBetDetail, joinBet, castVote, clearBetError } from "@/store/betSlice";
import { fetchMessages, clearChat } from "@/store/chatSlice";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useToast } from "@/components/shared/Toast";
import ChatWindow from "@/components/chat/ChatWindow";

const STATUS_LABELS: Record<string, string> = {
  open: "Aberta",
  locked: "Travada",
  voting: "Votacao",
  disputed: "Disputada",
  resolved: "Encerrada",
  cancelled: "Cancelada",
};

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

function getTimeRemaining(closesAt: string): string {
  const now = new Date();
  const closes = new Date(closesAt);
  const diff = closes.getTime() - now.getTime();

  if (diff <= 0) return "Encerrado";

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

  if (days > 0) return `${days}d ${hours}h restantes`;
  if (hours > 0) return `${hours}h ${minutes}min restantes`;
  return `${minutes}min restantes`;
}

export default function BetDetailPage() {
  const { betId } = useParams<{ betId: string }>();
  const dispatch = useDispatch<AppDispatch>();
  const { currentBet, loading, error } = useSelector(
    (state: RootState) => state.bets
  );
  const user = useSelector((state: RootState) => state.auth.user);

  const [selectedOption, setSelectedOption] = useState("");
  const [amount, setAmount] = useState(5);
  const [activeSection, setActiveSection] = useState<"details" | "chat">("details");

  const navigate = useNavigate();
  const { showToast } = useToast();
  const { messages, sendMessage, connected } = useWebSocket(betId);

  useEffect(() => {
    if (betId) {
      dispatch(fetchBetDetail(betId));
      dispatch(fetchMessages({ betId, page: 1 }));
    }
    return () => {
      dispatch(clearChat());
      dispatch(clearBetError());
    };
  }, [dispatch, betId]);

  useEffect(() => {
    if (error) {
      if (error.toLowerCase().includes("saldo insuficiente")) {
        showToast("Saldo insuficiente. Redirecionando para deposito...", "error");
        dispatch(clearBetError());
        setTimeout(() => navigate("/wallet"), 1500);
      } else {
        showToast(error, "error");
        dispatch(clearBetError());
      }
    }
  }, [error, showToast, dispatch, navigate]);

  const userParticipation = currentBet?.participations?.find(
    (p) => p.user_id === user?.id
  );

  const handleJoin = async () => {
    if (!betId || !selectedOption) return;
    const result = await dispatch(
      joinBet({ betId, optionId: selectedOption, amount })
    );
    if (joinBet.fulfilled.match(result)) {
      showToast("Voce entrou na aposta!", "success");
      dispatch(fetchBetDetail(betId));
    }
  };

  const handleVote = async (optionId: string) => {
    if (!betId) return;
    const result = await dispatch(castVote({ betId, optionId }));
    if (castVote.fulfilled.match(result)) {
      showToast("Voto registrado!", "success");
      dispatch(fetchBetDetail(betId));
    }
  };

  if (loading && !currentBet) {
    return (
      <div className="bet-detail-page">
        <div className="bets-loading">Carregando aposta...</div>
      </div>
    );
  }

  if (!currentBet) {
    return (
      <div className="bet-detail-page">
        <div className="bets-empty card">
          <p className="bets-empty-text">Aposta nao encontrada</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bet-detail-page">
      {/* Hero section */}
      <div className="bet-hero card">
        <div className="bet-hero-header">
          <span className={`category-tag category-${currentBet.category}`}>
            {CATEGORY_LABELS[currentBet.category] || currentBet.category}
          </span>
          <span className={`status-badge status-${currentBet.status}`}>
            {STATUS_LABELS[currentBet.status] || currentBet.status}
          </span>
        </div>
        <h1 className="bet-hero-title">{currentBet.title}</h1>
        {currentBet.description && (
          <p className="bet-hero-description">{currentBet.description}</p>
        )}
        <div className="bet-hero-meta">
          <span className="bet-meta-item">
            {currentBet.current_participants} participante{currentBet.current_participants !== 1 ? "s" : ""}
          </span>
          <span className="bet-meta-divider">|</span>
          <span className="bet-meta-item">
            Pote: {formatCurrency((currentBet.participations || []).reduce((sum, p) => sum + p.amount, 0))}
          </span>
        </div>
        <div className="bet-timer">
          {getTimeRemaining(currentBet.closes_at)}
        </div>
      </div>

      {/* Section tabs */}
      <div className="bets-tabs">
        <button
          className={`tab-btn ${activeSection === "details" ? "tab-active" : ""}`}
          onClick={() => setActiveSection("details")}
        >
          Detalhes
        </button>
        <button
          className={`tab-btn ${activeSection === "chat" ? "tab-active" : ""}`}
          onClick={() => setActiveSection("chat")}
        >
          Chat
        </button>
      </div>

      {activeSection === "details" && (
        <>
          {/* Options section */}
          <div className="bet-options card">
            <h3>Opcoes</h3>
            <div className="options-list">
              {currentBet.options.map((option) => {
                const isUserPick = userParticipation?.bet_option_id === option.id;
                const isWinner = option.is_winner;
                return (
                  <div
                    key={option.id}
                    className={`option-item ${isUserPick ? "option-selected" : ""} ${
                      isWinner ? "option-winner" : ""
                    }`}
                  >
                    <div className="option-info">
                      <span className="option-text">{option.label}</span>
                      <span className="option-count">
                        {(currentBet.participations || []).filter(p => p.bet_option_id === option.id).length} participante{(currentBet.participations || []).filter(p => p.bet_option_id === option.id).length !== 1 ? "s" : ""}
                      </span>
                    </div>
                    {isUserPick && (
                      <span className="option-your-pick">Sua escolha</span>
                    )}
                    {isWinner && (
                      <span className="option-winner-badge">Vencedora</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Join section - only if user hasn't joined and bet is open */}
          {!userParticipation && currentBet.status === "open" && (
            <div className="bet-join card">
              <h3>Entrar na aposta</h3>
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
              <div className="form-group">
                <label>
                  Valor (R$ {currentBet.min_entry} - R$ {currentBet.max_entry})
                </label>
                <input
                  type="number"
                  min={currentBet.min_entry}
                  max={currentBet.max_entry}
                  value={amount}
                  onChange={(e) => setAmount(Number(e.target.value))}
                />
              </div>
              <button
                className="btn btn-primary btn-full"
                onClick={handleJoin}
                disabled={!selectedOption || loading}
              >
                {loading ? "Entrando..." : "Entrar na aposta"}
              </button>
            </div>
          )}

          {/* Voting section */}
          {currentBet.status === "voting" && (
            <div className="bet-voting card">
              <h3>Votacao - Qual o resultado?</h3>
              <p className="form-hint">
                Vote na opcao que voce acredita ser a vencedora.
              </p>
              <div className="voting-options">
                {currentBet.options.map((option) => (
                  <button
                    key={option.id}
                    className="btn btn-secondary btn-full voting-btn"
                    onClick={() => handleVote(option.id)}
                    disabled={loading}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Participants section */}
          <div className="bet-participants card">
            <h3>Participantes ({currentBet.current_participants})</h3>
            {(currentBet.participations || []).length === 0 && (
              <p className="empty-state">Nenhum participante ainda</p>
            )}
            <div className="participants-list">
              {(currentBet.participations || []).map((p) => (
                <div key={p.id} className="participant-item">
                  <span className="participant-name">{p.username}</span>
                  <span className="participant-amount">
                    {formatCurrency(p.amount)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {activeSection === "chat" && (
        <ChatWindow
          messages={messages}
          onSendMessage={sendMessage}
          connected={connected}
          currentUserId={user?.id}
        />
      )}
    </div>
  );
}
