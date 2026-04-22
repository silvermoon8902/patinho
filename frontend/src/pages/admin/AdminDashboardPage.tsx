import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import type { RootState, AppDispatch } from "@/store";
import apiClient from "@/api/client";
import { useToast } from "@/components/shared/Toast";
import { Skeleton } from "@/components/shared/Skeleton";
import { fetchDashboardStats } from "@/store/adminSlice";
import { formatCurrency } from "@/utils/format";

export default function AdminDashboardPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { showToast } = useToast();
  const { stats, loading, error } = useSelector(
    (state: RootState) => state.admin
  );
  const [testingEmail, setTestingEmail] = useState(false);

  type EmailTestResult = {
    status: "sent" | "unconfigured" | "failed";
    detail: string;
    to?: string;
  };
  const [emailTestResult, setEmailTestResult] =
    useState<EmailTestResult | null>(null);

  useEffect(() => {
    dispatch(fetchDashboardStats());
  }, [dispatch]);

  const handleTestEmail = async () => {
    setTestingEmail(true);
    setEmailTestResult(null);
    try {
      const res = await apiClient.post("/admin/test-email", {});
      const d = res.data as {
        configured: boolean;
        sent: boolean;
        detail: string;
        to?: string;
      };
      if (d.sent) {
        setEmailTestResult({ status: "sent", detail: d.detail, to: d.to });
        showToast(`E-mail enviado para ${d.to}`, "success");
      } else if (!d.configured) {
        setEmailTestResult({ status: "unconfigured", detail: d.detail });
      } else {
        setEmailTestResult({ status: "failed", detail: d.detail });
      }
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } };
      setEmailTestResult({
        status: "failed",
        detail: e.response?.data?.detail || "Erro ao contatar o servidor",
      });
    } finally {
      setTestingEmail(false);
    }
  };

  return (
    <div className="admin-page">
      <h1 className="admin-page-title">Painel Administrativo</h1>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && !stats && (
        <div className="admin-stats-grid" aria-busy="true">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card admin-stat-card">
              <Skeleton width="60%" height={12} />
              <Skeleton width="80%" height={28} />
            </div>
          ))}
        </div>
      )}

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
        <div className="card admin-diag-card">
          <div className="admin-diag-row">
            <div className="admin-diag-info">
              <h3>SMTP</h3>
              <p>
                Envia um e-mail de teste para a sua conta admin para validar a
                configuração do servidor de e-mail.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleTestEmail}
              disabled={testingEmail}
            >
              {testingEmail ? "Enviando..." : "Enviar e-mail de teste"}
            </button>
          </div>

          {emailTestResult && (
            <div
              className={`admin-diag-result admin-diag-result-${emailTestResult.status}`}
              role="status"
            >
              <div className="admin-diag-result-header">
                <span className="admin-diag-result-icon" aria-hidden="true">
                  {emailTestResult.status === "sent"
                    ? "✓"
                    : emailTestResult.status === "unconfigured"
                    ? "i"
                    : "!"}
                </span>
                <strong>
                  {emailTestResult.status === "sent"
                    ? `E-mail enviado para ${emailTestResult.to}`
                    : emailTestResult.status === "unconfigured"
                    ? "SMTP ainda não configurado"
                    : "Falha no envio"}
                </strong>
              </div>
              <p>{emailTestResult.detail}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
