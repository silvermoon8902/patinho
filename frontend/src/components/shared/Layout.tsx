import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { HomeIcon, DiceIcon, WalletIcon, TrophyIcon, UserIcon } from "./Icons";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import { t } from "@/i18n";
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
              aria-label={t("action.back")}
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
          <div className="app-footer-links">
            <a href="/terms" className="app-footer-link">{t("footer.terms")}</a>
            <a href="/privacy" className="app-footer-link">{t("footer.privacy")}</a>
            <a href="/lgpd" className="app-footer-link">{t("footer.lgpd")}</a>
          </div>
          <a
            href="https://www.jogadoresanonimos.com.br/"
            target="_blank"
            rel="noopener noreferrer"
            className="app-footer-help"
          >
            <span aria-hidden="true" className="app-footer-help-icon">♥</span>
            {t("footer.responsible")}
          </a>
          <p className="app-footer-brand">{t("footer.tagline")}</p>
        </footer>
      </main>

      <nav className="bottom-nav">
        <NavLink to="/" className="nav-item" end>
          <HomeIcon size={22} />
          <span className="nav-label">{t("nav.home")}</span>
        </NavLink>
        <NavLink to="/bets" className="nav-item">
          <DiceIcon size={22} />
          <span className="nav-label">{t("nav.bets")}</span>
        </NavLink>
        <NavLink to="/wallet" className="nav-item">
          <WalletIcon size={22} />
          <span className="nav-label">{t("nav.wallet")}</span>
        </NavLink>
        <NavLink to="/ranking" className="nav-item">
          <TrophyIcon size={22} />
          <span className="nav-label">{t("nav.ranking")}</span>
        </NavLink>
        <NavLink to="/profile" className="nav-item">
          <UserIcon size={22} />
          <span className="nav-label">{t("nav.profile")}</span>
        </NavLink>
      </nav>
    </div>
  );
}
