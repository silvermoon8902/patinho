import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { fetchMyBets } from "@/store/betSlice";
import BetCard from "@/components/bets/BetCard";

type TabFilter = "active" | "resolved" | "all";

const TAB_STATUS_MAP: Record<TabFilter, string | undefined> = {
  active: "open",
  resolved: "resolved",
  all: undefined,
};

export default function BetsListPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { bets, loading, error } = useSelector(
    (state: RootState) => state.bets
  );
  const [activeTab, setActiveTab] = useState<TabFilter>("active");

  useEffect(() => {
    dispatch(fetchMyBets(TAB_STATUS_MAP[activeTab]));
  }, [dispatch, activeTab]);

  const handleTabChange = (tab: TabFilter) => {
    setActiveTab(tab);
  };

  return (
    <div className="bets-list-page">
      <div className="bets-header">
        <h1 className="page-title">Apostas</h1>
        <Link to="/bets/create" className="btn btn-primary btn-create-bet">
          Criar aposta
        </Link>
      </div>

      <div className="bets-tabs">
        <button
          className={`tab-btn ${activeTab === "active" ? "tab-active" : ""}`}
          onClick={() => handleTabChange("active")}
        >
          Ativas
        </button>
        <button
          className={`tab-btn ${activeTab === "resolved" ? "tab-active" : ""}`}
          onClick={() => handleTabChange("resolved")}
        >
          Encerradas
        </button>
        <button
          className={`tab-btn ${activeTab === "all" ? "tab-active" : ""}`}
          onClick={() => handleTabChange("all")}
        >
          Todas
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && (
        <div className="bets-loading">Carregando apostas...</div>
      )}

      {!loading && bets.length === 0 && (
        <div className="bets-empty card">
          <p className="bets-empty-text">Nenhuma aposta encontrada</p>
          <Link to="/bets/create" className="btn btn-primary">
            Criar sua primeira aposta
          </Link>
        </div>
      )}

      {!loading && bets.length > 0 && (
        <div className="bets-grid">
          {bets.map((bet) => (
            <BetCard key={bet.id} bet={bet} />
          ))}
        </div>
      )}
    </div>
  );
}
