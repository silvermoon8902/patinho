import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import {
  fetchLeagueDetail,
  fetchLeagueRanking,
  leaveLeague,
  deleteLeague,
  removeLeagueMember,
  clearCurrentLeague,
} from "@/store/leaguesSlice";
import { fetchMyBets } from "@/store/betSlice";
import BetCard from "@/components/bets/BetCard";
import { useToast } from "@/components/shared/Toast";
import { useConfirm } from "@/components/shared/ConfirmModal";
import InviteMemberModal from "./InviteMemberModal";

type TabKey = "members" | "ranking" | "bets";

export default function LeagueDetailPage() {
  const { leagueId } = useParams<{ leagueId: string }>();
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { showToast } = useToast();
  const confirm = useConfirm();

  const { currentLeague, ranking, loading, error } = useSelector(
    (state: RootState) => state.leagues
  );
  const { bets } = useSelector((state: RootState) => state.bets);

  const [activeTab, setActiveTab] = useState<TabKey>("members");
  const [inviteOpen, setInviteOpen] = useState(false);

  useEffect(() => {
    if (!leagueId) return;
    dispatch(fetchLeagueDetail(leagueId));
    return () => {
      dispatch(clearCurrentLeague());
    };
  }, [dispatch, leagueId]);

  useEffect(() => {
    if (!leagueId) return;
    if (activeTab === "ranking") {
      dispatch(fetchLeagueRanking(leagueId));
    } else if (activeTab === "bets") {
      dispatch(fetchMyBets({ leagueId }));
    }
  }, [dispatch, leagueId, activeTab]);

  const handleCopyCode = async () => {
    if (!currentLeague) return;
    try {
      await navigator.clipboard.writeText(currentLeague.invite_code);
      showToast("Código copiado", "success");
    } catch {
      showToast("Não foi possível copiar", "error");
    }
  };

  const handleLeave = async () => {
    if (!leagueId) return;
    const ok = await confirm({
      title: "Sair desta liga?",
      message:
        "Você perderá acesso aos desafios da liga. Desafios em que você já apostou continuarão visíveis até o encerramento.",
      confirmLabel: "Sair da liga",
      cancelLabel: "Cancelar",
      tone: "warning",
    });
    if (!ok) return;
    const result = await dispatch(leaveLeague(leagueId));
    if (leaveLeague.fulfilled.match(result)) {
      showToast("Você saiu da liga", "success");
      navigate("/leagues");
    } else {
      showToast(
        (result.payload as string) || "Erro ao sair da liga",
        "error"
      );
    }
  };

  const handleDelete = async () => {
    if (!leagueId) return;
    const ok = await confirm({
      title: "Excluir liga?",
      message:
        "Esta ação não pode ser desfeita. Só é possível excluir se não houver desafios ativos.",
      confirmLabel: "Excluir liga",
      cancelLabel: "Cancelar",
      tone: "danger",
    });
    if (!ok) return;
    const result = await dispatch(deleteLeague(leagueId));
    if (deleteLeague.fulfilled.match(result)) {
      showToast("Liga excluída", "success");
      navigate("/leagues");
    } else {
      showToast(
        (result.payload as string) || "Erro ao excluir a liga",
        "error"
      );
    }
  };

  const handleRemoveMember = async (userId: string, username: string) => {
    if (!leagueId) return;
    const ok = await confirm({
      title: `Remover ${username}?`,
      message:
        "Esse membro perderá o acesso aos desafios da liga. Pode ser adicionado novamente depois.",
      confirmLabel: "Remover membro",
      cancelLabel: "Cancelar",
      tone: "warning",
    });
    if (!ok) return;
    const result = await dispatch(
      removeLeagueMember({ leagueId, userId })
    );
    if (removeLeagueMember.fulfilled.match(result)) {
      showToast("Membro removido", "success");
    } else {
      showToast(
        (result.payload as string) || "Erro ao remover membro",
        "error"
      );
    }
  };

  if (loading && !currentLeague) {
    return <div className="bets-loading">Carregando liga...</div>;
  }

  if (error && !currentLeague) {
    return (
      <div className="league-detail-page">
        <div className="alert alert-error">{error}</div>
        <Link to="/leagues" className="btn btn-secondary">
          Voltar às ligas
        </Link>
      </div>
    );
  }

  if (!currentLeague) return null;

  const isOwner = currentLeague.is_owner;

  return (
    <div className="league-detail-page">
      <div className="league-detail-header">
        <div>
          <Link to="/leagues" className="league-back-link">
            {"<"} Voltar
          </Link>
          <h1 className="page-title">{currentLeague.name}</h1>
          {currentLeague.description && (
            <p className="league-detail-desc">{currentLeague.description}</p>
          )}
        </div>
        <div className="league-detail-code">
          <span className="league-card-code-label">Código de convite</span>
          <div className="league-invite-code-row">
            <span className="league-invite-code">
              {currentLeague.invite_code}
            </span>
            <button
              type="button"
              className="btn btn-secondary btn-copy-code"
              onClick={handleCopyCode}
            >
              Copiar
            </button>
          </div>
        </div>
      </div>

      <div className="bets-tabs league-tabs">
        <button
          className={`tab-btn ${activeTab === "members" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("members")}
        >
          Membros
        </button>
        <button
          className={`tab-btn ${activeTab === "ranking" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("ranking")}
        >
          Ranking
        </button>
        <button
          className={`tab-btn ${activeTab === "bets" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("bets")}
        >
          Desafios
        </button>
      </div>

      {activeTab === "members" && (
        <div className="league-members-list">
          {currentLeague.members.map((m) => (
            <div key={m.user_id} className="card league-member-row">
              <div>
                <span className="league-member-name">{m.username}</span>
                {m.is_owner && (
                  <span className="league-owner-badge">Dono</span>
                )}
              </div>
              {isOwner && !m.is_owner && (
                <button
                  className="btn btn-secondary btn-small"
                  onClick={() => handleRemoveMember(m.user_id, m.username)}
                >
                  Remover
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {activeTab === "ranking" && (
        <div className="league-ranking-list">
          {ranking.length === 0 && (
            <div className="bets-empty card">
              <p className="bets-empty-text">
                Ainda não há pontos registrados nesta liga
              </p>
            </div>
          )}
          {ranking.length > 0 && (
            <div className="card">
              <table className="league-ranking-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Jogador</th>
                    <th>Pontos</th>
                    <th>Vitórias</th>
                    <th>Desafios</th>
                  </tr>
                </thead>
                <tbody>
                  {ranking.map((entry, idx) => (
                    <tr key={entry.user_id}>
                      <td>{idx + 1}</td>
                      <td>{entry.username}</td>
                      <td>{entry.total_points}</td>
                      <td>{entry.wins}</td>
                      <td>{entry.participations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "bets" && (
        <div className="league-bets-list">
          {bets.length === 0 && (
            <div className="bets-empty card">
              <p className="bets-empty-text">
                Nenhum desafio nesta liga ainda
              </p>
              <Link to="/bets/create" className="btn btn-primary">
                Criar desafio na liga
              </Link>
            </div>
          )}
          {bets.length > 0 && (
            <div className="bets-grid">
              {bets.map((bet) => (
                <BetCard key={bet.id} bet={bet} />
              ))}
            </div>
          )}
        </div>
      )}

      <div className="league-detail-actions">
        {isOwner && (
          <button
            className="btn btn-primary"
            onClick={() => setInviteOpen(true)}
          >
            Convidar amigos
          </button>
        )}
        {!isOwner && currentLeague.is_member && (
          <button className="btn btn-secondary" onClick={handleLeave}>
            Sair da liga
          </button>
        )}
        {isOwner && (
          <button className="btn btn-danger" onClick={handleDelete}>
            Excluir liga
          </button>
        )}
      </div>

      <InviteMemberModal
        open={inviteOpen}
        leagueId={currentLeague.id}
        onClose={() => setInviteOpen(false)}
      />
    </div>
  );
}
