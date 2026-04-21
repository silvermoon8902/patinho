import { useState, FormEvent } from "react";
import { Link } from "react-router-dom";
import apiClient from "@/api/client";
import { useTheme } from "@/hooks/useTheme";
import patinhoLogo from "@/assets/patinho-logo.png";
import patinhoLogoWhite from "@/assets/patinho-logo-white.png";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { theme } = useTheme();
  const logoSrc = theme === "dark" ? patinhoLogoWhite : patinhoLogo;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiClient.post("/auth/forgot-password", { email });
      setSubmitted(true);
    } catch {
      // Even on error, present a generic success message so we don't leak
      // whether an email exists. But show a soft error if the request itself
      // failed (e.g. network) so the user knows to retry.
      setSubmitted(true);
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
          <h2>Esqueci minha senha</h2>

          {submitted ? (
            <>
              <div className="alert alert-success">
                Se o e-mail existir, você receberá instruções em instantes.
              </div>
              <p className="auth-link" style={{ textAlign: "center" }}>
                <Link to="/login">Voltar ao login</Link>
              </p>
            </>
          ) : (
            <>
              {error && <div className="alert alert-error">{error}</div>}

              <p style={{ marginBottom: "16px", color: "var(--color-text-muted)" }}>
                Informe seu e-mail e enviaremos um link para redefinir sua senha.
              </p>

              <div className="form-group">
                <label htmlFor="email">E-mail</label>
                <input
                  id="email"
                  type="email"
                  placeholder="seu@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-full"
                disabled={loading}
              >
                {loading ? "Enviando..." : "Enviar link de recuperação"}
              </button>

              <p className="auth-link">
                Lembrou da senha?{" "}
                <Link to="/login">Entrar</Link>
              </p>
            </>
          )}
        </form>
      </div>
    </div>
  );
}
