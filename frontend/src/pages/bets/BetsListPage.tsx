import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { fetchMyBets } from "@/store/betSlice";
import BetCard from "@/components/bets/BetCard";
import { SkeletonBetCard } from "@/components/shared/Skeleton";
import EmptyState from "@/components/shared/EmptyState";

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
  // Tracks whether the user has ANY bets (across all statuses). Computed
  // from an unfiltered fetch on mount so the empty-state copy can
  // distinguish "brand new user" from "nothing in this tab right now".
  const [hasAnyBets, setHasAnyBets] = useState<boolean | null>(null);

  useEffect(() => {
    dispatch(fetchMyBets(TAB_STATUS_MAP[activeTab]));
  }, [dispatch, activeTab]);

  useEffect(() => {
    // One-shot: determine if the user has any bets in any state.
    let cancelled = false;
    dispatch(fetchMyBets(undefined)).then((result) => {
      if (cancelled) return;
      const payload = (result as { payload?: unknown }).payload;
      if (Array.isArray(payload)) {
        setHasAnyBets(payload.length > 0);
      }
    });
    return () => {
      cancelled = true;
    };
    // Intentionally run only once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTabChange = (tab: TabFilter) => {
    setActiveTab(tab);
  };

  return (
    <div className="bets-list-page">
      <div className="bets-header">
        <h1 className="page-title">Desafios</h1>
        <Link to="/bets/create" className="btn btn-primary btn-create-bet">
          Criar desafio
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
        <div className="bets-grid" aria-busy="true">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonBetCard key={i} />
          ))}
        </div>
      )}

      {!loading && bets.length === 0 && (
        <EmptyState
          icon="bets"
          title={
            hasAnyBets === false
              ? "Você ainda não tem desafios"
              : activeTab === "active"
              ? "Nenhum desafio ativo no momento"
              : activeTab === "resolved"
              ? "Nenhum desafio encerrado ainda"
              : "Você ainda não tem desafios"
          }
          description={
            hasAnyBets === false
              ? "Crie seu primeiro desafio e convide seus amigos para participar."
              : activeTab === "resolved"
              ? "Quando seus desafios forem encerrados, o histórico aparece aqui."
              : "Pronto para criar um novo?"
          }
          action={
            <>
              {hasAnyBets === false && activeTab !== "resolved" && (
                <Link to="/bets/create" className="btn btn-primary">
                  Criar seu primeiro desafio
                </Link>
              )}
              {hasAnyBets && activeTab === "resolved" && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setActiveTab("active")}
                >
                  Ver desafios ativos
                </button>
              )}
              {hasAnyBets && activeTab === "active" && (
                <Link to="/bets/create" className="btn btn-primary">
                  Criar novo desafio
                </Link>
              )}
            </>
          }
        />
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
