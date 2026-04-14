import { NavLink, Outlet } from "react-router-dom";
import { HomeIcon, DiceIcon, WalletIcon, TrophyIcon, UserIcon } from "./Icons";
import patinhoLogo from "@/assets/patinho-logo.png";

export default function Layout() {
  return (
    <div className="layout">
      <header className="header">
        <div className="header-content">
          <img src={patinhoLogo} alt="Patinho" className="logo-image" />
        </div>
      </header>

      <main className="main-content">
        <Outlet />
      </main>

      <nav className="bottom-nav">
        <NavLink to="/" className="nav-item" end>
          <HomeIcon size={22} />
          <span className="nav-label">Inicio</span>
        </NavLink>
        <NavLink to="/bets" className="nav-item">
          <DiceIcon size={22} />
          <span className="nav-label">Apostas</span>
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
