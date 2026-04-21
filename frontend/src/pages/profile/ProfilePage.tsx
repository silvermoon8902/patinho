import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/components/shared/Toast";
import apiClient from "@/api/client";

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const { showToast } = useToast();

  const [username, setUsername] = useState(user?.username || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [saving, setSaving] = useState(false);
  const [depositCap, setDepositCap] = useState<string>(
    user?.monthly_deposit_cap ? String(user.monthly_deposit_cap) : ""
  );
  const [participationCap, setParticipationCap] = useState<string>(
    user?.monthly_participation_cap ? String(user.monthly_participation_cap) : ""
  );
  const [limitsSaving, setLimitsSaving] = useState(false);
  const [deleteConfirmEmail, setDeleteConfirmEmail] = useState("");
  const [deleteConfirmPassword, setDeleteConfirmPassword] = useState("");
  const [deleting, setDeleting] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiClient.put("/users/me", { username, phone });
      showToast("Perfil atualizado!", "success");
    } catch {
      showToast("Erro ao atualizar perfil", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    window.location.href = "/login";
  };

  const handleSaveLimits = async () => {
    setLimitsSaving(true);
    try {
      await apiClient.patch("/users/me/limits", {
        monthly_deposit_cap: depositCap === "" ? null : parseFloat(depositCap),
        monthly_participation_cap:
          participationCap === "" ? null : parseFloat(participationCap),
      });
      showToast("Limites atualizados", "success");
    } catch {
      showToast("Erro ao salvar limites", "error");
    } finally {
      setLimitsSaving(false);
    }
  };

  const handleExport = async () => {
    try {
      const res = await apiClient.get("/users/me/export");
      const blob = new Blob([JSON.stringify(res.data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `patinho-meus-dados-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast("Exportação concluída", "success");
    } catch {
      showToast("Erro ao exportar dados", "error");
    }
  };

  const handleSelfExclude = async () => {
    if (
      !window.confirm(
        "Tem certeza? Sua conta será desativada imediatamente. Para reativar, será necessário contatar o suporte."
      )
    )
      return;
    try {
      await apiClient.post("/users/me/self-exclude", { confirm: true });
      showToast("Conta desativada", "success");
      await logout();
      window.location.href = "/login";
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } };
      showToast(e.response?.data?.detail || "Erro ao desativar conta", "error");
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmEmail !== user?.email) {
      showToast("Email de confirmação não confere", "error");
      return;
    }
    if (!deleteConfirmPassword) {
      showToast("Digite sua senha para confirmar", "error");
      return;
    }
    if (
      !window.confirm(
        "Excluir a conta é irreversível. Seus dados pessoais serão apagados. Deseja continuar?"
      )
    )
      return;
    setDeleting(true);
    try {
      await apiClient.request({
        method: "DELETE",
        url: "/users/me",
        data: {
          confirm_email: deleteConfirmEmail,
          password: deleteConfirmPassword,
        },
      });
      showToast("Conta excluída", "success");
      await logout();
      window.location.href = "/login";
    } catch (err) {
      const e = err as { response?: { data?: { detail?: string } } };
      showToast(e.response?.data?.detail || "Erro ao excluir conta", "error");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="profile-page">
      <div className="card profile-header">
        <div className="profile-avatar">
          {user?.username?.charAt(0).toUpperCase() || "P"}
        </div>
        <h1 className="profile-name">{user?.username}</h1>
        <p className="profile-email">{user?.email}</p>
      </div>

      <div className="card">
        <h3>Editar perfil</h3>
        <div className="form-group">
          <label htmlFor="username">Nome de usuário</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            minLength={3}
          />
        </div>
        <div className="form-group">
          <label htmlFor="phone">Telefone</label>
          <input
            id="phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </div>
        <button
          className="btn btn-primary btn-full"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "Salvando..." : "Salvar alterações"}
        </button>
      </div>

      <div className="card">
        <h3>Conta</h3>
        <div className="profile-info-row">
          <span className="profile-info-label">E-mail</span>
          <span className="profile-info-value">{user?.email}</span>
        </div>
        <div className="profile-info-row">
          <span className="profile-info-label">Pontos</span>
          <span className="profile-info-value">{user?.total_points || 0}</span>
        </div>
        {user?.is_admin && (
          <div className="profile-info-row">
            <span className="profile-info-label">Tipo</span>
            <span className="profile-info-value profile-admin-badge">Administrador</span>
          </div>
        )}
      </div>

      <div className="card">
        <h3>Limites mensais (jogo responsável)</h3>
        <p className="form-hint">
          Defina um teto para os seus próprios depósitos e apostas por mês. Deixe em branco ou 0 para remover o limite.
        </p>
        <div className="form-group">
          <label htmlFor="depositCap">Limite de depósito (R$ / mês)</label>
          <input
            id="depositCap"
            type="number"
            min="0"
            step="1"
            value={depositCap}
            onChange={(e) => setDepositCap(e.target.value)}
            placeholder="Ex: 500"
          />
        </div>
        <div className="form-group">
          <label htmlFor="participationCap">Limite de entradas (R$ / mês)</label>
          <input
            id="participationCap"
            type="number"
            min="0"
            step="1"
            value={participationCap}
            onChange={(e) => setParticipationCap(e.target.value)}
            placeholder="Ex: 200"
          />
        </div>
        <button
          className="btn btn-primary btn-full"
          onClick={handleSaveLimits}
          disabled={limitsSaving}
        >
          {limitsSaving ? "Salvando..." : "Salvar limites"}
        </button>
      </div>

      <div className="card">
        <h3>Seus dados (LGPD)</h3>
        <p className="form-hint">
          Você tem direito a acessar, exportar ou excluir os seus dados a qualquer momento.
        </p>
        <button
          type="button"
          className="btn btn-secondary btn-full"
          onClick={handleExport}
          style={{ marginBottom: "8px" }}
        >
          Exportar meus dados (JSON)
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-full"
          onClick={handleSelfExclude}
        >
          Desativar minha conta
        </button>
      </div>

      <div className="card">
        <h3>Excluir conta permanentemente</h3>
        <p className="form-hint">
          Esta ação é irreversível. Seus dados pessoais serão apagados; registros
          históricos de apostas serão anonimizados para fins de auditoria.
        </p>
        <div className="form-group">
          <label htmlFor="deleteEmail">Digite seu e-mail para confirmar</label>
          <input
            id="deleteEmail"
            type="email"
            value={deleteConfirmEmail}
            onChange={(e) => setDeleteConfirmEmail(e.target.value)}
            placeholder={user?.email || ""}
          />
        </div>
        <div className="form-group">
          <label htmlFor="deletePwd">Senha atual</label>
          <input
            id="deletePwd"
            type="password"
            value={deleteConfirmPassword}
            onChange={(e) => setDeleteConfirmPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        <button
          type="button"
          className="btn btn-danger btn-full"
          onClick={handleDeleteAccount}
          disabled={deleting}
        >
          {deleting ? "Excluindo..." : "Excluir minha conta"}
        </button>
      </div>

      <button
        className="btn btn-secondary btn-full profile-logout-btn"
        onClick={handleLogout}
      >
        Sair da conta
      </button>
    </div>
  );
}
