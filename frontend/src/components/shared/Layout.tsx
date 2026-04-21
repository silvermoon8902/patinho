import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { HomeIcon, DiceIcon, WalletIcon, TrophyIcon, UserIcon } from "./Icons";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import ThemeToggle from "./ThemeToggle";
import patinhoLogo from "@/assets/patinho-logo.png";
import patinhoLogoWhite from "@/assets/patinho-logo-white.png";

const TOP_LEVEL_PATHS = new Set([
  "/",
  "/bets",
  "/wallet",
  "/ranking",
  "/profile",
  "/leagues",
]);

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { theme } = useTheme();
  const showBack = !TOP_LEVEL_PATHS.has(location.pathname);
  const isInAdminArea = location.pathname.startsWith("/admin");
  const showAdminShortcut = user?.is_admin && !isInAdminArea;
  const logoSrc = theme === "dark" ? patinhoLogoWhite : patinhoLogo;

  return (
    <div className="layout">
      <header className="header">
        <div className="header-content">
          {showBack && (
            <button
              type="button"
              className="header-back"
              onClick={() => navigate(-1)}
              aria-label="Voltar"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
          )}
          <img src={logoSrc} alt="Patinho" className="logo-image" />
          <div className="header-actions">
            <ThemeToggle />
          </div>
          {showAdminShortcut && (
            <button
              type="button"
              className="header-admin-btn"
              onClick={() => navigate("/admin")}
              aria-label="Ir para painel admin"
            >
              Admin
            </button>
          )}
        </div>
      </header>

      <main className="main-content">
        <Outlet />
        <footer className="app-footer">
          <a href="/terms">Termos</a>
          <span aria-hidden="true">·</span>
          <a href="/privacy">Privacidade</a>
          <span aria-hidden="true">·</span>
          <a href="/lgpd">LGPD</a>
          <span aria-hidden="true">·</span>
          <a
            href="https://www.jogadoresanonimos.com.br/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Jogo responsável
          </a>
        </footer>
      </main>

      <nav className="bottom-nav">
        <NavLink to="/" className="nav-item" end>
          <HomeIcon size={22} />
          <span className="nav-label">Início</span>
        </NavLink>
        <NavLink to="/bets" className="nav-item">
          <DiceIcon size={22} />
          <span className="nav-label">Desafios</span>
        </NavLink>
        <NavLink to="/wallet" className="nav-item">
          <WalletIcon size={22} />
          <span className="nav-label">Carteira</span>
        </NavLink>
        <NavLink to="/ranking" className="nav-item">
          <TrophyIcon size={22} />
          <span className="nav-label">Ranking</span>
        </NavLink>
        <NavLink to="/profile" className="nav-item">
          <UserIcon size={22} />
          <span className="nav-label">Perfil</span>
        </NavLink>
      </nav>
    </div>
  );
}
