import React from "react";
import { Link } from "react-router-dom";
import type { BetResponse } from "@/store/betSlice";
import { formatCurrency } from "@/utils/format";
import { shareInvite } from "@/utils/share";

const STATUS_LABELS: Record<string, string> = {
  open: "Aberta",
  locked: "Travada",
  pending_confirmation: "Aguardando Confirmação",
  voting: "Votação",
  disputed: "Disputada",
  resolved: "Encerrada",
  cancelled: "Cancelada",
};

const CATEGORY_LABELS: Record<string, string> = {
  football: "Futebol",
  f1: "Fórmula 1",
  tennis: "Tênis",
  bbb: "BBB",
  politics: "Politica",
  custom: "Outro",
};

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
  const handleShare = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Bet cards in lists fire shares straight away with the long URL —
    // shortening here would block navigator.share on iOS. The detail
    // page is where users see the TinyURL via its prefetched state.
    const inviteUrl = `${window.location.origin}/invite/${bet.invite_token}`;
    void shareInvite({
      title: `Patinho · ${bet.title}`,
      url: inviteUrl,
      text: `Você foi convidado para o desafio "${bet.title}" no Patinho! Clique no link para ver as regras e participar:`,
    });
  };

  return (
    <Link to={`/bets/${bet.id}`} className="bet-card card">
      <div className="bet-card-header">
        <span className={`category-tag category-${bet.category}`}>
          {CATEGORY_LABELS[bet.category] || bet.category}
        </span>
        <div className="bet-card-header-right">
          <button
            className="btn-share-card"
            onClick={handleShare}
            title="Compartilhar no WhatsApp"
            type="button"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="18" cy="5" r="3"/>
              <circle cx="6" cy="12" r="3"/>
              <circle cx="18" cy="19" r="3"/>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
            </svg>
          </button>
          <span className={`status-badge status-${bet.status}`}>
            {STATUS_LABELS[bet.status] || bet.status}
          </span>
        </div>
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
          <span className="bet-stat-label">Entrada</span>
          <span className="bet-stat-value">{formatCurrency(bet.entry_amount)}</span>
        </div>
        <div className="bet-stat">
          <span className="bet-stat-label">Encerra em</span>
          <span className="bet-stat-value">{getTimeRemaining(bet.closes_at)}</span>
        </div>
      </div>
    </Link>
  );
}
