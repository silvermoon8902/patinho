import { useState, useEffect, useRef, FormEvent } from "react";
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

  // One-shot guard so StrictMode double-mount + React re-renders can't
  // chain multiple navigate() calls for the same auth transition.
  const hasRedirected = useRef(false);

  // Read these through refs so the redirect effect doesn't re-fire every
  // time user data is refreshed from /users/me.
  const explicitFrom = (location.state as { from?: string })?.from;
  const redirectQuery = searchParams.get("redirect");
  const destinationRef = useRef<string>("/");
  destinationRef.current =
    redirectQuery || explicitFrom || (user?.is_admin ? "/admin" : "/");

  // Only depend on the boolean. `user` can update independently (fetchMe
  // fires after login) but the destination is always captured via ref.
  useEffect(() => {
    if (isAuthenticated && !hasRedirected.current) {
      hasRedirected.current = true;
      navigate(destinationRef.current, { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    resetError();
    // `resetError` from useAuth is a fresh closure each render; we only
    // want this to clear once on mount, so intentionally omit it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

          <p className="auth-link" style={{ textAlign: "right", marginTop: "-8px", marginBottom: "16px" }}>
            <Link to="/forgot-password">Esqueci minha senha</Link>
          </p>

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={loading}
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>

          <p className="auth-link">
            Não tem conta?{" "}
            <Link to="/register">Criar conta</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
