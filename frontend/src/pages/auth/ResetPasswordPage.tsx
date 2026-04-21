import { useState, FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import apiClient from "@/api/client";
import { useTheme } from "@/hooks/useTheme";
import { useToast } from "@/components/shared/Toast";
import patinhoLogo from "@/assets/patinho-logo.png";
import patinhoLogoWhite from "@/assets/patinho-logo-white.png";

export default function ResetPasswordPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { theme } = useTheme();
  const logoSrc = theme === "dark" ? patinhoLogoWhite : patinhoLogo;

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("A senha deve ter pelo menos 8 caracteres");
      return;
    }
    if (password !== confirmPassword) {
      setError("As senhas não coincidem");
      return;
    }
    if (!token) {
      setError("Token inválido");
      return;
    }

    setLoading(true);
    try {
      await apiClient.post("/auth/reset-password", {
        token,
        new_password: password,
      });
      showToast("Senha redefinida com sucesso. Faça login.", "success");
      navigate("/login", { replace: true });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setError(detail || "Não foi possível redefinir a senha. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-logo">
          <img src={logoSrc} alt="Patinho" className="auth-logo-image" />
          <p className="auth-subtitle">Desafios entre Amigos</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>Redefinir senha</h2>

          {error && <div className="alert alert-error">{error}</div>}

          <p style={{ marginBottom: "16px", color: "var(--color-text-muted)" }}>
            Escolha uma nova senha para sua conta.
          </p>

          <div className="form-group">
            <label htmlFor="password">Nova senha</label>
            <input
              id="password"
              type="password"
              placeholder="Mínimo 8 caracteres"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirmar senha</label>
            <input
              id="confirmPassword"
              type="password"
              placeholder="Repita a nova senha"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={loading}
          >
            {loading ? "Redefinindo..." : "Redefinir senha"}
          </button>

          <p className="auth-link">
            Lembrou da senha?{" "}
            <Link to="/login">Entrar</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
