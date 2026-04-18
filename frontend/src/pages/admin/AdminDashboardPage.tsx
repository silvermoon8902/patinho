import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import type { RootState, AppDispatch } from "@/store";
import { fetchDashboardStats } from "@/store/adminSlice";

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export default function AdminDashboardPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { stats, loading, error } = useSelector(
    (state: RootState) => state.admin
  );

  useEffect(() => {
    dispatch(fetchDashboardStats());
  }, [dispatch]);

  return (
    <div className="admin-page">
      <h1 className="admin-page-title">Painel Administrativo</h1>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && !stats && <p className="empty-state">Carregando...</p>}

      {stats && (
        <div className="admin-stats-grid">
          <div className="admin-stat-card card">
            <span className="admin-stat-label">Total de Usuarios</span>
            <span className="admin-stat-value">{stats.total_users}</span>
          </div>
          <div className="admin-stat-card card">
            <span className="admin-stat-label">Total de Desafios</span>
            <span className="admin-stat-value">{stats.total_bets}</span>
          </div>
          <div className="admin-stat-card card">
            <span className="admin-stat-label">Desafios Ativos</span>
            <span className="admin-stat-value">{stats.active_bets}</span>
          </div>
          <div className="admin-stat-card card">
            <span className="admin-stat-label">Receita Total</span>
            <span className="admin-stat-value">
              {formatCurrency(stats.total_revenue)}
            </span>
          </div>
          <div className="admin-stat-card card">
            <span className="admin-stat-label">Total Depositado</span>
            <span className="admin-stat-value">
              {formatCurrency(stats.total_deposits)}
            </span>
          </div>
        </div>
      )}

      <div className="admin-quick-links">
        <h2>Acesso Rapido</h2>
        <div className="admin-links-grid">
          <Link to="/admin/users" className="admin-link-card card">
            <span className="admin-link-title">Usuarios</span>
            <span className="admin-link-desc">
              Gerenciar usuarios da plataforma
            </span>
          </Link>
          <Link to="/admin/bets" className="admin-link-card card">
            <span className="admin-link-title">Desafios</span>
            <span className="admin-link-desc">
              Gerenciar e resolver desafios
            </span>
          </Link>
          <Link to="/admin/fee" className="admin-link-card card">
            <span className="admin-link-title">Taxa</span>
            <span className="admin-link-desc">
              Configurar taxa da plataforma
            </span>
          </Link>
        </div>
      </div>
    </div>
  );
}
