import { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import type { RootState, AppDispatch } from "@/store";
import { fetchWallet } from "@/store/walletSlice";
import { fetchMyBets } from "@/store/betSlice";
import { useAuth } from "@/hooks/useAuth";
import { formatCurrency } from "@/utils/format";

export default function DashboardPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useAuth();
  const { wallet } = useSelector((state: RootState) => state.wallet);
  const { bets } = useSelector((state: RootState) => state.bets);

  useEffect(() => {
    dispatch(fetchWallet());
    dispatch(fetchMyBets(undefined));
  }, [dispatch]);

  const activeBolao = useMemo(
    () =>
      bets.find(
        (b) =>
          b.template?.startsWith("bolao_") &&
          b.status !== "resolved" &&
          b.status !== "cancelled"
      ) || null,
    [bets]
  );
  const activeBetsCount = useMemo(
    () =>
      bets.filter((b) => b.status === "open" || b.status === "locked")
        .length,
    [bets]
  );

  return (
    <div className="dashboard-page">
      <div className="welcome-section">
        <h1>Olá, {user?.username || "Jogador"}!</h1>
        <p>Bem-vindo ao Patinho</p>
      </div>

      <div className="stats-grid">
        <div className="card stat-card">
          <span className="stat-label">Saldo</span>
          <span className="stat-value">
            {wallet ? formatCurrency(wallet.balance) : "R$ 0,00"}
          </span>
        </div>
        <div className="card stat-card">
          <span className="stat-label">Desafios ativos</span>
          <span className="stat-value">{activeBetsCount}</span>
        </div>
      </div>

      {activeBolao && (
        <Link
          to={`/bets/${activeBolao.id}/palpites`}
          className="card bolao-dashboard-card"
        >
          <div className="bolao-dashboard-content">
            <span className="bolao-dashboard-tag">Bolão em andamento</span>
            <strong className="bolao-dashboard-title">
              {activeBolao.title}
            </strong>
            <p className="bolao-dashboard-desc">
              Faça seus palpites e acompanhe o ranking ao vivo.
            </p>
          </div>
          <span className="bolao-dashboard-cta" aria-hidden="true">→</span>
        </Link>
      )}

      <div className="quick-actions">
        <h2>Ações rápidas</h2>
        <div className="actions-grid">
          <Link to="/bets/create" className="card action-card">
            <span className="action-label">Criar Desafio</span>
          </Link>
          <Link to="/wallet" className="card action-card">
            <span className="action-label">Depositar</span>
          </Link>
          <Link to="/ranking" className="card action-card">
            <span className="action-label">Ver Ranking</span>
          </Link>
          <Link to="/leagues" className="card action-card">
            <span className="action-label">Ligas</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
