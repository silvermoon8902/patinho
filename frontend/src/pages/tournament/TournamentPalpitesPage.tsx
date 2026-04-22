import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import {
  fetchTournamentFixtures,
  submitPalpitesBulk,
  submitChampionPalpite,
  type TournamentFixture,
} from "@/store/tournamentSlice";
import { useToast } from "@/components/shared/Toast";

const PHASE_LABEL: Record<string, string> = {
  group: "Fase de grupos",
  ko_16: "Oitavas de final",
  ko_8: "Quartas de final",
  semifinal: "Semifinal",
  final: "Final",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

function isLocked(locksAt: string): boolean {
  return new Date(locksAt).getTime() <= Date.now();
}

export default function TournamentPalpitesPage() {
  const { betId } = useParams<{ betId: string }>();
  const dispatch = useDispatch<AppDispatch>();
  const { showToast } = useToast();
  const { fixtures, loading, saving, error } = useSelector(
    (state: RootState) => state.tournament
  );

  const [edited, setEdited] = useState<
    Record<string, { home: string; away: string }>
  >({});
  const [champion, setChampion] = useState("");
  const [savingChamp, setSavingChamp] = useState(false);

  useEffect(() => {
    if (betId) dispatch(fetchTournamentFixtures(betId));
  }, [betId, dispatch]);

  const byPhase = useMemo(() => {
    const groups: Record<string, TournamentFixture[]> = {};
    for (const f of fixtures) {
      (groups[f.phase || "group"] ??= []).push(f);
    }
    return groups;
  }, [fixtures]);

  const phaseOrder = ["group", "ko_16", "ko_8", "semifinal", "final"];

  const handleScoreChange = (
    fid: string,
    side: "home" | "away",
    value: string
  ) => {
    const cleaned = value.replace(/[^0-9]/g, "").slice(0, 2);
    setEdited((prev) => {
      const cur = prev[fid] || { home: "", away: "" };
      return { ...prev, [fid]: { ...cur, [side]: cleaned } };
    });
  };

  const handleSaveAll = async () => {
    if (!betId) return;
    const toSubmit = fixtures
      .filter((f) => {
        if (isLocked(f.locks_at)) return false;
        const e = edited[f.fixture_id];
        if (!e) return false;
        if (e.home === "" || e.away === "") return false;
        return true;
      })
      .map((f) => ({
        fixture_id: f.fixture_id,
        home_score: parseInt(edited[f.fixture_id]!.home, 10),
        away_score: parseInt(edited[f.fixture_id]!.away, 10),
        phase: f.phase,
        locks_at: f.locks_at,
      }));

    if (toSubmit.length === 0) {
      showToast("Nenhum palpite novo para salvar", "info");
      return;
    }

    const result = await dispatch(
      submitPalpitesBulk({ betId, palpites: toSubmit })
    );
    if (submitPalpitesBulk.fulfilled.match(result)) {
      const { saved, rejected_locked } = result.payload;
      if (saved > 0) {
        showToast(
          `${saved} palpite${saved > 1 ? "s" : ""} salvo${saved > 1 ? "s" : ""}` +
            (rejected_locked
              ? ` · ${rejected_locked} partida${rejected_locked > 1 ? "s" : ""} já iniciada${rejected_locked > 1 ? "s" : ""}`
              : ""),
          "success"
        );
        setEdited({});
        dispatch(fetchTournamentFixtures(betId));
      } else {
        showToast("Partidas já iniciadas, palpites não aceitos", "info");
      }
    }
  };

  const handleSaveChampion = async () => {
    if (!betId || champion.trim().length < 2) {
      showToast("Digite o nome do campeão", "error");
      return;
    }
    setSavingChamp(true);
    try {
      const result = await dispatch(
        submitChampionPalpite({ betId, team: champion.trim() })
      );
      if (submitChampionPalpite.fulfilled.match(result)) {
        showToast(`Campeão: ${result.payload.predicted_champion}`, "success");
      }
    } finally {
      setSavingChamp(false);
    }
  };

  const unsavedCount = Object.values(edited).filter(
    (e) => e.home !== "" && e.away !== ""
  ).length;

  return (
    <div className="tournament-palpites-page">
      <header className="legal-hero">
        <span className="legal-status-pill legal-status-active">Bolão da Copa</span>
        <h1 className="legal-title">Seus palpites</h1>
        <p className="legal-subtitle">
          Palpite em cada partida até 10 minutos antes do apito inicial.
          Acertar o resultado vale 3 pts, acertar o placar exato vale 6 pts.
          Nas eliminatórias os pontos dobram. Acertar o campeão vale 30 pts
          extras no final.
        </p>
        <div className="palpite-hero-actions">
          <Link
            to={`/bets/${betId}`}
            className="btn btn-secondary"
          >
            Voltar ao desafio
          </Link>
          <Link
            to={`/bets/${betId}/ranking`}
            className="btn btn-primary"
          >
            Ver ranking ao vivo
          </Link>
        </div>
      </header>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="card champion-card">
        <h3>Palpite do campeão (30 pts)</h3>
        <p className="form-hint">
          Digite o nome do país que você acha que vai levantar a taça. Pode
          alterar até o início da fase final.
        </p>
        <div className="champion-form-row">
          <input
            className="form-input"
            type="text"
            placeholder="Ex: Brasil, Argentina, França"
            value={champion}
            onChange={(e) => setChampion(e.target.value)}
            maxLength={80}
          />
          <button
            className="btn btn-primary"
            onClick={handleSaveChampion}
            disabled={savingChamp}
          >
            {savingChamp ? "Salvando..." : "Salvar"}
          </button>
        </div>
      </section>

      {loading && <div className="bets-loading" aria-busy="true">Carregando partidas…</div>}
      {!loading && fixtures.length === 0 && (
        <div className="bets-empty card">
          <p className="bets-empty-text">
            As partidas aparecerão aqui assim que o calendário for publicado.
          </p>
        </div>
      )}

      {!loading &&
        phaseOrder
          .filter((ph) => (byPhase[ph] || []).length > 0)
          .map((ph) => (
            <section key={ph} className="card phase-card">
              <h3>{PHASE_LABEL[ph] || ph}</h3>
              <ul className="palpite-list">
                {byPhase[ph]!.map((f) => {
                  const locked = isLocked(f.locks_at);
                  const current =
                    edited[f.fixture_id] ??
                    (f.my_palpite
                      ? {
                          home: String(f.my_palpite.home_score ?? ""),
                          away: String(f.my_palpite.away_score ?? ""),
                        }
                      : { home: "", away: "" });
                  return (
                    <li
                      key={f.fixture_id}
                      className={`palpite-row ${locked ? "palpite-row-locked" : ""}`}
                    >
                      <div className="palpite-meta">
                        <span className="palpite-date">
                          {formatDate(f.kickoff_at)}
                        </span>
                        {f.my_palpite && f.my_palpite.points_earned > 0 && (
                          <span className="palpite-points">
                            +{f.my_palpite.points_earned} pts
                          </span>
                        )}
                        {locked && (
                          <span className="palpite-locked-badge">Encerrado</span>
                        )}
                      </div>
                      <div className="palpite-teams">
                        <div className="palpite-team">
                          {f.home_logo && (
                            <img
                              src={f.home_logo}
                              alt={f.home_team || ""}
                              className="palpite-team-logo"
                            />
                          )}
                          <span>{f.home_team || "TBD"}</span>
                        </div>
                        <div className="palpite-scores">
                          <input
                            type="text"
                            inputMode="numeric"
                            className="palpite-score-input"
                            value={current.home}
                            disabled={locked}
                            onChange={(e) =>
                              handleScoreChange(
                                f.fixture_id,
                                "home",
                                e.target.value
                              )
                            }
                          />
                          <span className="palpite-scores-x">×</span>
                          <input
                            type="text"
                            inputMode="numeric"
                            className="palpite-score-input"
                            value={current.away}
                            disabled={locked}
                            onChange={(e) =>
                              handleScoreChange(
                                f.fixture_id,
                                "away",
                                e.target.value
                              )
                            }
                          />
                        </div>
                        <div className="palpite-team palpite-team-away">
                          <span>{f.away_team || "TBD"}</span>
                          {f.away_logo && (
                            <img
                              src={f.away_logo}
                              alt={f.away_team || ""}
                              className="palpite-team-logo"
                            />
                          )}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}

      {!loading && fixtures.length > 0 && (
        <div className="palpite-save-bar">
          <span className="palpite-save-count">
            {unsavedCount > 0
              ? `${unsavedCount} palpite${unsavedCount > 1 ? "s" : ""} pendente${unsavedCount > 1 ? "s" : ""}`
              : "Nenhum palpite pendente"}
          </span>
          <button
            className="btn btn-primary"
            onClick={handleSaveAll}
            disabled={saving || unsavedCount === 0}
          >
            {saving ? "Salvando..." : "Salvar palpites"}
          </button>
        </div>
      )}
    </div>
  );
}
