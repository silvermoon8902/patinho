import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import type { RootState, AppDispatch } from "@/store";
import { fetchWallet } from "@/store/walletSlice";
import { useAuth } from "@/hooks/useAuth";
import { formatCurrency } from "@/utils/format";

export default function DashboardPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useAuth();
  const { wallet } = useSelector((state: RootState) => state.wallet);

  useEffect(() => {
    dispatch(fetchWallet());
  }, [dispatch]);

  return (
    <div className="dashboard-page">
      <div className="welcome-section">
        <h1>Ola, {user?.username || "Jogador"}!</h1>
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
          <span className="stat-value">0</span>
        </div>
      </div>

      <div className="quick-actions">
        <h2>Acoes rapidas</h2>
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
        </div>
      </div>
    </div>
  );
}
