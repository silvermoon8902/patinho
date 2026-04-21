import { useState, useEffect, FormEvent } from "react";
import { useNavigate, Link, useLocation, useSearchParams } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import patinhoLogo from "@/assets/patinho-logo.png";
import patinhoLogoWhite from "@/assets/patinho-logo-white.png";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { login, isAuthenticated, user, loading, error, resetError } = useAuth();
  const { theme } = useTheme();
  const logoSrc = theme === "dark" ? patinhoLogoWhite : patinhoLogo;
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const explicitFrom = (location.state as { from?: string })?.from;
  const redirectQuery = searchParams.get("redirect");

  useEffect(() => {
    if (isAuthenticated) {
      const destination = redirectQuery || explicitFrom || (user?.is_admin ? "/admin" : "/");
      navigate(destination, { replace: true });
    }
  }, [isAuthenticated, user, navigate, explicitFrom, redirectQuery]);

  useEffect(() => {
    resetError();
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await login(email, password);
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-logo">
          <img src={logoSrc} alt="Patinho" className="auth-logo-image" />
          <p className="auth-subtitle">Desafios entre Amigos</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>Entrar</h2>

          {error && <div className="alert alert-error">{error}</div>}

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

          <div className="form-group">
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              placeholder="Sua senha"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={loading}
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>

          <p className="auth-link">
            Nao tem conta?{" "}
            <Link to="/register">Criar conta</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
