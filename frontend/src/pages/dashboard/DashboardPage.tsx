import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import type { RootState, AppDispatch } from "@/store";
import { fetchWallet } from "@/store/walletSlice";
import { useAuth } from "@/hooks/useAuth";
import trophyImg from "@/assets/trophy.jpg";
import liveImg from "@/assets/live.jpg";
import friendsImg from "@/assets/friends.jpg";
import soccerImg from "@/assets/soccer.jpg";
import tvImg from "@/assets/tv.jpg";
import targetImg from "@/assets/target.jpg";
import emptyImg from "@/assets/empty.jpg";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

const categories = [
  { id: "popular", label: "Populares", image: trophyImg },
  { id: "live", label: "Ao Vivo", image: liveImg },
  { id: "friends", label: "Amigos", image: friendsImg },
  { id: "soccer", label: "Futebol", image: soccerImg },
  { id: "bbb", label: "BBB", image: tvImg },
  { id: "custom", label: "Custom", image: targetImg },
];

const FEATURED_IMAGE = trophyImg;
const EMPTY_IMAGE = emptyImg;

export default function DashboardPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useAuth();
  const { wallet } = useSelector((state: RootState) => state.wallet);
  const [activeCategory, setActiveCategory] = useState("popular");

  useEffect(() => {
    dispatch(fetchWallet());
  }, [dispatch]);

  const balance = wallet?.balance ?? 0;

  return (
    <div className="dashboard-dark">
      {/* Hero: welcome + CTA */}
      <div className="dash-hero">
        <div className="dash-hero-left">
          <div className="dash-hero-greeting">Ola, {user?.username || "Jogador"}!</div>
          <div className="dash-balance-row">
            <div>
              <div className="dash-balance-label">Saldo disponivel</div>
              <div className="dash-balance-value">{formatCurrency(balance)}</div>
            </div>
            <Link to="/wallet" className="dash-hero-action">Depositar</Link>
          </div>
        </div>
        <div className="dash-hero-right">
          <Link to="/bets/create" className="dash-hero-cta">
            <img src={FEATURED_IMAGE} alt="Trofeu" className="dash-hero-cta-image" />
            <div className="dash-hero-cta-text">
              <div className="dash-hero-cta-title">Criar nova aposta</div>
              <div className="dash-hero-cta-subtitle">Desafie seus amigos</div>
            </div>
          </Link>
        </div>
      </div>

      {/* Category pills */}
      <div className="dash-categories">
        {categories.map((cat) => (
          <button
            key={cat.id}
            className={`dash-category ${activeCategory === cat.id ? "active" : ""}`}
            onClick={() => setActiveCategory(cat.id)}
          >
            <img src={cat.image} alt={cat.label} className="dash-category-image" />
            <span className="dash-category-label">{cat.label}</span>
          </button>
        ))}
      </div>

      {/* Featured combo card */}
      <div className="dash-section">
        <div className="dash-section-header">
          <h2 className="dash-section-title">Destaque</h2>
          <span className="dash-section-link">Ola, {user?.username || "Jogador"}!</span>
        </div>
        <div className="dash-combo-card">
          <img src={FEATURED_IMAGE} alt="Destaque" className="dash-combo-image" />
          <div className="dash-combo-text">
            <div className="dash-combo-title">Aposta em destaque</div>
            <div className="dash-combo-subtitle">Comece a jogar agora</div>
          </div>
          <div className="dash-combo-badge">NOVO</div>
        </div>
      </div>

      {/* Active bets */}
      <div className="dash-section">
        <div className="dash-section-header">
          <h2 className="dash-section-title">Suas apostas ativas</h2>
          <Link to="/bets" className="dash-section-link">Ver todas</Link>
        </div>
        <div className="dash-empty-bets">
          <img src={EMPTY_IMAGE} alt="Sem apostas" className="dash-empty-image" />
          <div className="dash-empty-text">
            <div className="dash-empty-title">Nenhuma aposta ativa</div>
            <div className="dash-empty-subtitle">Crie ou entre em uma aposta</div>
          </div>
          <Link to="/bets/create" className="dash-empty-cta">Criar</Link>
        </div>
      </div>

      {/* Popular / Featured */}
      <div className="dash-section">
        <div className="dash-section-header">
          <h2 className="dash-section-title">Em alta</h2>
        </div>
        <div className="dash-hot-placeholder">
          <p>Em breve: apostas populares da comunidade</p>
        </div>
      </div>
    </div>
  );
}
