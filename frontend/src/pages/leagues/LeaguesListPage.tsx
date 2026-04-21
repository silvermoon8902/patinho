import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { fetchMyLeagues } from "@/store/leaguesSlice";
import CreateLeagueModal from "./CreateLeagueModal";
import JoinByCodeModal from "./JoinByCodeModal";

export default function LeaguesListPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { myLeagues, loading, error } = useSelector(
    (state: RootState) => state.leagues
  );
  const [createOpen, setCreateOpen] = useState(false);
  const [joinOpen, setJoinOpen] = useState(false);

  useEffect(() => {
    dispatch(fetchMyLeagues());
  }, [dispatch]);

  return (
    <div className="leagues-list-page">
      <div className="bets-header">
        <h1 className="page-title">Minhas Ligas</h1>
        <div className="league-header-actions">
          <button
            className="btn btn-secondary"
            onClick={() => setJoinOpen(true)}
          >
            Entrar com código
          </button>
          <button
            className="btn btn-primary"
            onClick={() => setCreateOpen(true)}
          >
            Criar nova liga
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && myLeagues.length === 0 && (
        <div className="bets-loading">Carregando ligas...</div>
      )}

      {!loading && myLeagues.length === 0 && (
        <div className="bets-empty card">
          <p className="bets-empty-text">
            Você ainda não faz parte de nenhuma liga
          </p>
          <button
            className="btn btn-primary"
            onClick={() => setCreateOpen(true)}
          >
            Criar sua primeira liga
          </button>
        </div>
      )}

      {myLeagues.length > 0 && (
        <div className="leagues-grid">
          {myLeagues.map((league) => (
            <Link
              key={league.id}
              to={`/leagues/${league.id}`}
              className="card league-card"
            >
              <div className="league-card-header">
                <h3 className="league-card-title">{league.name}</h3>
                <span className="league-card-count">
                  {league.member_count}{" "}
                  {league.member_count === 1 ? "membro" : "membros"}
                </span>
              </div>
              {league.description && (
                <p className="league-card-desc">{league.description}</p>
              )}
              <div className="league-card-footer">
                <span className="league-card-code-label">Código:</span>
                <span className="league-invite-code">
                  {league.invite_code}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      <CreateLeagueModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />
      <JoinByCodeModal
        open={joinOpen}
        onClose={() => setJoinOpen(false)}
      />
    </div>
  );
}
