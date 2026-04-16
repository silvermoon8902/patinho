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
  const [linkCopied, setLinkCopied] = useState(false);

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

  const getInviteUrl = () => {
    if (!currentBet) return "";
    return `${window.location.origin}/invite/${currentBet.invite_token}`;
  };

  const handleShareWhatsApp = () => {
    if (!currentBet) return;
    const message = `Entra na minha aposta no Patinho! \u{1F3B2}\n${currentBet.title}\n${getInviteUrl()}`;
    const url = `https://wa.me/?text=${encodeURIComponent(message)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleCopyInviteLink = async () => {
    const url = getInviteUrl();
    try {
      await navigator.clipboard.writeText(url);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = url;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    }
  };

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

      {/* Share section */}
      <div className="share-section card">
        <h3>Compartilhar</h3>
        <div className="share-buttons">
          <button
            className="btn btn-whatsapp"
            onClick={handleShareWhatsApp}
            type="button"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
            </svg>
            WhatsApp
          </button>
          <button
            className="btn btn-copy-link"
            onClick={handleCopyInviteLink}
            type="button"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
            {linkCopied ? "Copiado!" : "Copiar link"}
          </button>
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
