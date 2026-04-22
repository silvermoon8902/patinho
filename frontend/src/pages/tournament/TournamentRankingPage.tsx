import { useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { fetchTournamentRanking } from "@/store/tournamentSlice";

export default function TournamentRankingPage() {
  const { betId } = useParams<{ betId: string }>();
  const dispatch = useDispatch<AppDispatch>();
  const ranking = useSelector((state: RootState) => state.tournament.ranking);

  useEffect(() => {
    if (!betId) return;
    dispatch(fetchTournamentRanking(betId));
    const id = setInterval(() => {
      dispatch(fetchTournamentRanking(betId));
    }, 60_000);
    return () => clearInterval(id);
  }, [betId, dispatch]);

  return (
    <div className="tournament-ranking-page">
      <header className="legal-hero">
        <span className="legal-status-pill legal-status-active">Ranking ao vivo</span>
        <h1 className="legal-title">Classificação do bolão</h1>
        <p className="legal-subtitle">
          Atualizado a cada 60 segundos. Em caso de empate no final, o prêmio é
          dividido igualmente entre os líderes.
        </p>
        <div className="palpite-hero-actions">
          <Link to={`/bets/${betId}/palpites`} className="btn btn-secondary">
            Voltar aos palpites
          </Link>
          <Link to={`/bets/${betId}`} className="btn btn-primary">
            Detalhes do desafio
          </Link>
        </div>
      </header>

      {ranking.length === 0 ? (
        <div className="bets-empty card">
          <p className="bets-empty-text">
            O ranking vai aparecer assim que as primeiras partidas forem apuradas.
          </p>
        </div>
      ) : (
        <section className="card">
          <ul className="ranking-list">
            {ranking.map((r) => (
              <li key={r.user_id} className={`ranking-row rank-${Math.min(r.rank, 3)}`}>
                <span className="ranking-rank">{r.rank}</span>
                <span className="ranking-username">{r.username}</span>
                <span className="ranking-points">{r.points} pts</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
