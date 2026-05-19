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
import apiClient from "@/api/client";
import { shareInvite, copyToClipboard } from "@/utils/share";

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
  // Prefetched share URL — populated on league load so the WhatsApp
  // click is synchronous (iOS Safari requires that for navigator.share).
  const [shareUrl, setShareUrl] = useState<string>("");

  useEffect(() => {
    if (!leagueId) return;
    dispatch(fetchLeagueDetail(leagueId));
    return () => {
      dispatch(clearCurrentLeague());
    };
  }, [dispatch, leagueId]);

  useEffect(() => {
    const code = currentLeague?.invite_code;
    if (!code) return;
    let cancelled = false;
    const long = `${window.location.origin}/leagues/join/${code}`;
    setShareUrl(long);
    apiClient
      .get(`/leagues/${code}/short-url`, { timeout: 4000 })
      .then((r) => {
        if (cancelled) return;
        const u = r.data?.short_url;
        if (typeof u === "string" && u) setShareUrl(u);
      })
      .catch(() => {
        /* keep the long-url fallback */
      });
    return () => {
      cancelled = true;
    };
  }, [currentLeague?.invite_code]);

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
    const ok = await copyToClipboard(currentLeague.invite_code);
    showToast(ok ? "Código copiado" : "Não foi possível copiar", ok ? "success" : "error");
  };

  const handleCopyLink = async () => {
    if (!currentLeague) return;
    const ok = await copyToClipboard(shareUrl);
    showToast(ok ? "Link copiado" : "Não foi possível copiar", ok ? "success" : "error");
  };

  const handleShareWhatsApp = () => {
    if (!currentLeague || !shareUrl) return;
    // Fire synchronously — using the prefetched shareUrl. Any await here
    // would break navigator.share on iOS Safari.
    void shareInvite({
      title: `Patinho · Liga ${currentLeague.name}`,
      url: shareUrl,
      text: `Entre na liga "${currentLeague.name}" no Patinho! Toque no link para participar:`,
    });
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
    return <div className="bets-loading" aria-busy="true">Carregando liga…</div>;
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
              Copiar código
            </button>
          </div>
          <div
            className="share-buttons"
            style={{ marginTop: "10px" }}
          >
            <button
              type="button"
              className="btn btn-whatsapp"
              onClick={handleShareWhatsApp}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
              </svg>
              WhatsApp
            </button>
            <button
              type="button"
              className="btn btn-copy-link"
              onClick={handleCopyLink}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
              </svg>
              Copiar link
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
