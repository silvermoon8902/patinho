import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { fetchBetDetail, joinBet, castVote, clearBetError } from "@/store/betSlice";
import { fetchMessages, clearChat } from "@/store/chatSlice";
import { useWebSocket } from "@/hooks/useWebSocket";
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

  const userParticipation = currentBet?.participants.find(
    (p) => p.user_id === user?.id
  );

  const handleJoin = async () => {
    if (!betId || !selectedOption) return;
    await dispatch(
      joinBet({ betId, optionId: selectedOption, amount })
    );
  };

  const handleVote = async (optionId: string) => {
    if (!betId) return;
    await dispatch(castVote({ betId, optionId }));
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
            {currentBet.participant_count} participante{currentBet.participant_count !== 1 ? "s" : ""}
          </span>
          <span className="bet-meta-divider">|</span>
          <span className="bet-meta-item">
            Pote: {formatCurrency(currentBet.total_pot)}
          </span>
        </div>
        <div className="bet-timer">
          {getTimeRemaining(currentBet.closes_at)}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

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
                const isUserPick = userParticipation?.option_id === option.id;
                const isWinner = currentBet.winning_option_id === option.id;
                return (
                  <div
                    key={option.id}
                    className={`option-item ${isUserPick ? "option-selected" : ""} ${
                      isWinner ? "option-winner" : ""
                    }`}
                  >
                    <div className="option-info">
                      <span className="option-text">{option.text}</span>
                      <span className="option-count">
                        {option.participant_count} participante{option.participant_count !== 1 ? "s" : ""}
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
                      {opt.text}
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
                    {option.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Participants section */}
          <div className="bet-participants card">
            <h3>Participantes ({currentBet.participant_count})</h3>
            {currentBet.participants.length === 0 && (
              <p className="empty-state">Nenhum participante ainda</p>
            )}
            <div className="participants-list">
              {currentBet.participants.map((p) => (
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
