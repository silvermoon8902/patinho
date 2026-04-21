import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import type { RootState, AppDispatch } from "@/store";
import apiClient from "@/api/client";
import { useToast } from "@/components/shared/Toast";
import { fetchDashboardStats } from "@/store/adminSlice";
import { formatCurrency } from "@/utils/format";

export default function AdminDashboardPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { showToast } = useToast();
  const { stats, loading, error } = useSelector(
    (state: RootState) => state.admin
  );
  const [testingEmail, setTestingEmail] = useState(false);

  useEffect(() => {
    dispatch(fetchDashboardStats());
  }, [dispatch]);

  const handleTestEmail = async () => {
    setTestingEmail(true);
    try {
      const res = await apiClient.post("/admin/test-email", {});
      const d = res.data as {
        configured: boolean;
        sent: boolean;
        detail: string;
        to?: string;
      };
      if (d.sent) {
        showToast(`E-mail enviado para ${d.to}`, "success");
      } else {
        showToast(d.detail || "Envio não realizado", "info");
      }
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } };
      showToast(e.response?.data?.detail || "Erro", "error");
    } finally {
      setTestingEmail(false);
    }
  };

  return (
    <div className="admin-page">
      <h1 className="admin-page-title">Painel Administrativo</h1>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && !stats && <p className="empty-state">Carregando...</p>}

      {stats && (
        <div className="admin-stats-grid">
          <div className="admin-stat-card card">
            <span className="admin-stat-label">Total de Usuários</span>
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
        <h2>Acesso Rápido</h2>
        <div className="admin-links-grid">
          <Link to="/admin/users" className="admin-link-card card">
            <span className="admin-link-title">Usuários</span>
            <span className="admin-link-desc">
              Gerenciar usuários da plataforma
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

      <div className="admin-quick-links">
        <h2>Diagnóstico</h2>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleTestEmail}
          disabled={testingEmail}
        >
          {testingEmail ? "Enviando..." : "Enviar e-mail de teste (SMTP)"}
        </button>
      </div>
    </div>
  );
}
