import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import {
  fetchLeaderboard,
  fetchWeeklyLeaderboard,
  fetchUserRank,
  fetchUserBadges,
} from "@/store/rankingSlice";
import type { LeaderboardEntry, BadgeItem } from "@/store/rankingSlice";

const CATEGORY_COLORS: Record<string, string> = {
  participation: "#4F46E5",
  creation: "#0891B2",
  victory: "#D97706",
  streak: "#DC2626",
  social: "#059669",
  prize: "#7C3AED",
};

function PodiumCard({
  entry,
  place,
}: {
  entry: LeaderboardEntry;
  place: 1 | 2 | 3;
}) {
  const placeLabels = { 1: "1o", 2: "2o", 3: "3o" };
  const placeClasses = {
    1: "podium-gold",
    2: "podium-silver",
    3: "podium-bronze",
  };

  return (
    <div className={`podium-card ${placeClasses[place]}`}>
      <div className="podium-place">{placeLabels[place]}</div>
      <div className="podium-username">{entry.username}</div>
      <div className="podium-points">{entry.points} pts</div>
    </div>
  );
}

function BadgeCard({ badge }: { badge: BadgeItem }) {
  const color = CATEGORY_COLORS[badge.category] || "#6b7280";

  return (
    <div className={`badge-card ${badge.earned ? "badge-earned" : "badge-locked"}`}>
      <div
        className="badge-circle"
        style={{
          backgroundColor: badge.earned ? color : "#e5e7eb",
          color: badge.earned ? "#fff" : "#9ca3af",
        }}
      >
        {badge.icon}
      </div>
      <div className="badge-info">
        <span className="badge-name">{badge.name}</span>
        <span className="badge-description">{badge.description}</span>
      </div>
    </div>
  );
}

export default function RankingPage() {
  const dispatch = useDispatch<AppDispatch>();
  const {
    leaderboard,
    weeklyLeaderboard,
    userRank,
    badges,
    loading,
  } = useSelector((state: RootState) => state.ranking);

  const [activeTab, setActiveTab] = useState<"global" | "weekly">("global");

  useEffect(() => {
    dispatch(fetchLeaderboard());
    dispatch(fetchWeeklyLeaderboard());
    dispatch(fetchUserRank());
    dispatch(fetchUserBadges());
  }, [dispatch]);

  const currentList =
    activeTab === "global" ? leaderboard : weeklyLeaderboard;
  const top3 = currentList.slice(0, 3);
  const rest = currentList.slice(3);

  const currentUserRankData =
    activeTab === "global" ? userRank?.global : userRank?.weekly;

  return (
    <div className="ranking-page">
      <h1 className="page-title">Ranking</h1>

      {/* Tab toggle */}
      <div className="ranking-tabs">
        <button
          className={`tab-btn ${activeTab === "global" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("global")}
        >
          Geral
        </button>
        <button
          className={`tab-btn ${activeTab === "weekly" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("weekly")}
        >
          Semanal
        </button>
      </div>

      {/* User's rank highlight */}
      {userRank && currentUserRankData && (
        <div className="ranking-user-card card">
          <span className="ranking-user-label">Sua posicao</span>
          <div className="ranking-user-stats">
            <span className="ranking-user-rank">
              {currentUserRankData.rank
                ? `${currentUserRankData.rank}o`
                : "-"}
            </span>
            <span className="ranking-user-points">
              {currentUserRankData.points} pts
            </span>
          </div>
        </div>
      )}

      {loading && <p className="ranking-loading">Carregando...</p>}

      {/* Top 3 podium */}
      {top3.length > 0 && (
        <div className="podium-section">
          {top3[1] && <PodiumCard entry={top3[1]} place={2} />}
          {top3[0] && <PodiumCard entry={top3[0]} place={1} />}
          {top3[2] && <PodiumCard entry={top3[2]} place={3} />}
        </div>
      )}

      {/* Leaderboard table */}
      {rest.length > 0 && (
        <div className="leaderboard-table card">
          {rest.map((entry) => (
            <div
              key={entry.user_id}
              className={`leaderboard-row ${
                userRank && entry.user_id === userRank.user_id
                  ? "leaderboard-row-highlight"
                  : ""
              }`}
            >
              <span className="leaderboard-rank">{entry.rank}o</span>
              <span className="leaderboard-username">{entry.username}</span>
              <span className="leaderboard-points">{entry.points} pts</span>
            </div>
          ))}
        </div>
      )}

      {!loading && currentList.length === 0 && (
        <div className="empty-state">Nenhum jogador no ranking ainda</div>
      )}

      {/* Badges section */}
      <div className="badges-section">
        <h2 className="badges-title">Suas conquistas</h2>
        <div className="badges-grid">
          {badges.map((badge) => (
            <BadgeCard key={badge.id} badge={badge} />
          ))}
        </div>
        {badges.length === 0 && !loading && (
          <div className="empty-state">Nenhuma conquista disponível</div>
        )}
      </div>
    </div>
  );
}
