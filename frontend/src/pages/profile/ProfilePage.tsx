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
          <label htmlFor="username">Nome de usuario</label>
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
          {saving ? "Salvando..." : "Salvar alteracoes"}
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

      <button
        className="btn btn-secondary btn-full profile-logout-btn"
        onClick={handleLogout}
      >
        Sair da conta
      </button>
    </div>
  );
}
