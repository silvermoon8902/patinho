import { Link } from "react-router-dom";
import type { BetResponse } from "@/store/betSlice";

const STATUS_LABELS: Record<string, string> = {
  open: "Aberta",
  locked: "Travada",
  voting: "Votacao",
  disputed: "Disputada",
  resolved: "Encerrada",
  cancelled: "Cancelada",
};

const CATEGORY_LABELS: Record<string, string> = {
  football: "Futebol",
  f1: "F1",
  tennis: "Tenis",
  bbb: "BBB",
  politics: "Politica",
  custom: "Outro",
};

function formatCurrency(value: number): string {
  return `R$ ${value.toFixed(2).replace(".", ",")}`;
}

function getTimeRemaining(closesAt: string): string {
  const now = new Date();
  const closes = new Date(closesAt);
  const diff = closes.getTime() - now.getTime();

  if (diff <= 0) return "Encerrado";

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}min`;
  return `${minutes}min`;
}

interface BetCardProps {
  bet: BetResponse;
}

export default function BetCard({ bet }: BetCardProps) {
  return (
    <Link to={`/bets/${bet.id}`} className="bet-card card">
      <div className="bet-card-header">
        <span className={`category-tag category-${bet.category}`}>
          {CATEGORY_LABELS[bet.category] || bet.category}
        </span>
        <span className={`status-badge status-${bet.status}`}>
          {STATUS_LABELS[bet.status] || bet.status}
        </span>
      </div>
      <h3 className="bet-card-title">{bet.title}</h3>
      <div className="bet-card-stats">
        <div className="bet-stat">
          <span className="bet-stat-label">Participantes</span>
          <span className="bet-stat-value">{bet.current_participants}</span>
        </div>
        <div className="bet-stat">
          <span className="bet-stat-label">Pote total</span>
          <span className="bet-stat-value">{formatCurrency((bet.participations || []).reduce((sum, p) => sum + p.amount, 0))}</span>
        </div>
        <div className="bet-stat">
          <span className="bet-stat-label">Encerra em</span>
          <span className="bet-stat-value">{getTimeRemaining(bet.closes_at)}</span>
        </div>
      </div>
    </Link>
  );
}
