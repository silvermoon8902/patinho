import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { createBet } from "@/store/betSlice";
import {
  clearDrivers,
  clearFixtures,
  clearRaces,
  clearTennisMatches,
  createSportBet,
  fetchFixtures,
  fetchLeagues,
  fetchRaceDrivers,
  fetchRaces,
  fetchTennisMatches,
} from "@/store/sportsSlice";
import { fetchMyLeagues } from "@/store/leaguesSlice";

type BetFlow = "none" | "sport" | "custom";
type SportKind = "football" | "f1" | "tennis";
type TennisTour = "ATP" | "WTA" | "";

const CUSTOM_STEPS = ["Informações", "Opções", "Regras", "Revisão"];
const SPORT_STEPS = ["Esporte", "Evento", "Aposta", "Regras", "Revisão"];

const MIN_ENTRY = 5;
const MAX_ENTRY = 1000;
const MIN_PARTICIPANTS = 2;
const MAX_PARTICIPANTS = 100;

const MIN_DRIVERS = 2;
const MAX_DRIVERS = 10;

const F1_SEASONS = [2026, 2025];

interface SportTemplate {
  id: string;
  label: string;
  description: string;
  sport: SportKind;
}

const SPORT_TEMPLATES: SportTemplate[] = [
  {
    id: "match_winner",
    label: "Quem vence?",
    description: "Escolha o vencedor da partida (ou empate)",
    sport: "football",
  },
  {
    id: "exact_score",
    label: "Acertar o placar",
    description: "Escolha o placar exato da partida",
    sport: "football",
  },
  {
    id: "f1_winner",
    label: "Vencedor da corrida",
    description: "Escolha o piloto que vai vencer a corrida",
    sport: "f1",
  },
  {
    id: "tennis_winner",
    label: "Vencedor da partida",
    description: "Escolha o vencedor da partida de tênis",
    sport: "tennis",
  },
];

const EXACT_SCORE_OPTIONS = [
  "0x0",
  "1x0",
  "0x1",
  "1x1",
  "2x0",
  "0x2",
  "2x1",
  "1x2",
  "Outro",
];

function formatFixtureDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function CreateBetPage() {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { loading: customLoading, error: customError } = useSelector(
    (state: RootState) => state.bets
  );
  const { myLeagues } = useSelector((state: RootState) => state.leagues);
  const {
    leagues,
    leaguesLoading,
    leaguesError,
    fixtures,
    fixturesLoading,
    fixturesError,
    fixturesLeagueId,
    fixturesReason,
    races,
    racesLoading,
    racesError,
    racesSeason,
    drivers,
    driversLoading,
    driversError,
    driversRaceId,
    tennisMatches,
    tennisMatchesLoading,
    tennisMatchesError,
    tennisMatchesTour,
    createLoading: sportCreateLoading,
    createError: sportCreateError,
  } = useSelector((state: RootState) => state.sports);

  const [flow, setFlow] = useState<BetFlow>("none");
  const [step, setStep] = useState(0);

  // Custom flow state. Custom bets always use voting resolution (auto-resolution
  // lives in the sport flow), and category is forced to "custom" so the category
  // dropdown is unnecessary for invitees and for the creator.
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const category = "custom";
  const [options, setOptions] = useState(["", ""]);
  const resolutionType: "voting" = "voting";
  const MIN_DESCRIPTION = 20;
  const [entryAmountText, setEntryAmountText] = useState(String(MIN_ENTRY));
  const [maxParticipantsText, setMaxParticipantsText] = useState("100");
  const [closesAt, setClosesAt] = useState("");

  // Sport flow state
  const [sportKind, setSportKind] = useState<SportKind>("football");
  const [selectedLeagueId, setSelectedLeagueId] = useState<string | null>(null);
  const [selectedFixtureId, setSelectedFixtureId] = useState<string | null>(
    null
  );
  const [selectedSeason, setSelectedSeason] = useState<number>(F1_SEASONS[0]!);
  const [selectedRaceId, setSelectedRaceId] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] =
    useState<string>("match_winner");
  const [selectedDriverIds, setSelectedDriverIds] = useState<string[]>([]);
  const [driversInitialized, setDriversInitialized] = useState(false);
  const [sportEntryAmountText, setSportEntryAmountText] = useState(
    String(MIN_ENTRY)
  );
  const [sportMaxParticipantsText, setSportMaxParticipantsText] =
    useState("100");

  // Optional private league scope for the new bet (applies to both flows)
  const [privateLeagueId, setPrivateLeagueId] = useState<string>("");

  // Tennis-specific state
  const [selectedTennisTour, setSelectedTennisTour] =
    useState<TennisTour>("ATP");
  const [selectedTennisMatchId, setSelectedTennisMatchId] = useState<
    string | null
  >(null);

  const entryAmount = parseFloat(entryAmountText) || 0;
  const maxParticipants = parseInt(maxParticipantsText) || 0;
  const sportEntryAmount = parseFloat(sportEntryAmountText) || 0;
  const sportMaxParticipants = parseInt(sportMaxParticipantsText) || 0;

  const selectedLeague = leagues.find((l) => l.id === selectedLeagueId) || null;
  const selectedFixture =
    fixtures.find((f) => f.fixture_id === selectedFixtureId) || null;
  const selectedRace =
    races.find((r) => r.race_id === selectedRaceId) || null;
  const selectedTennisMatch =
    tennisMatches.find((m) => m.match_id === selectedTennisMatchId) || null;

  const availableTemplates = SPORT_TEMPLATES.filter(
    (t) => t.sport === sportKind
  );
  const selectedTemplateData =
    availableTemplates.find((t) => t.id === selectedTemplate) || null;

  // Load user's private leagues once the wizard starts (for optional scoping)
  useEffect(() => {
    if (flow !== "none" && myLeagues.length === 0) {
      dispatch(fetchMyLeagues());
    }
  }, [flow, myLeagues.length, dispatch]);

  // Fetch leagues when user enters the sport flow with football.
  useEffect(() => {
    if (
      flow === "sport" &&
      sportKind === "football" &&
      leagues.length === 0 &&
      !leaguesLoading
    ) {
      dispatch(fetchLeagues());
    }
  }, [flow, sportKind, leagues.length, leaguesLoading, dispatch]);

  // Fetch fixtures when a league is selected on the Evento step.
  useEffect(() => {
    if (
      flow === "sport" &&
      sportKind === "football" &&
      step === 1 &&
      selectedLeagueId &&
      !fixturesLoading &&
      fixturesLeagueId !== selectedLeagueId
    ) {
      dispatch(fetchFixtures({ leagueId: selectedLeagueId }));
    }
  }, [
    flow,
    sportKind,
    step,
    selectedLeagueId,
    fixturesLoading,
    fixturesLeagueId,
    dispatch,
  ]);

  // Fetch F1 races when user reaches the Evento step for F1.
  useEffect(() => {
    if (
      flow === "sport" &&
      sportKind === "f1" &&
      step === 1 &&
      !racesLoading &&
      racesSeason !== selectedSeason
    ) {
      dispatch(fetchRaces(selectedSeason));
    }
  }, [flow, sportKind, step, selectedSeason, racesLoading, racesSeason, dispatch]);

  // Fetch drivers when user reaches the Aposta step for F1 with a race picked.
  useEffect(() => {
    if (
      flow === "sport" &&
      sportKind === "f1" &&
      step === 2 &&
      selectedRaceId &&
      !driversLoading &&
      driversRaceId !== selectedRaceId
    ) {
      setDriversInitialized(false);
      dispatch(fetchRaceDrivers(selectedRaceId));
    }
  }, [
    flow,
    sportKind,
    step,
    selectedRaceId,
    driversLoading,
    driversRaceId,
    dispatch,
  ]);

  // Fetch tennis matches when user reaches the Evento step for Tennis.
  useEffect(() => {
    if (
      flow === "sport" &&
      sportKind === "tennis" &&
      step === 1 &&
      !tennisMatchesLoading &&
      tennisMatchesTour !== selectedTennisTour
    ) {
      dispatch(
        fetchTennisMatches({ tour: selectedTennisTour, season: F1_SEASONS[0]! })
      );
    }
  }, [
    flow,
    sportKind,
    step,
    selectedTennisTour,
    tennisMatchesLoading,
    tennisMatchesTour,
    dispatch,
  ]);

  // Once drivers arrive, default-select up to the first 10 by driver_id
  useEffect(() => {
    if (
      flow === "sport" &&
      sportKind === "f1" &&
      !driversLoading &&
      drivers.length > 0 &&
      !driversInitialized &&
      driversRaceId === selectedRaceId
    ) {
      setSelectedDriverIds(drivers.slice(0, MAX_DRIVERS).map((d) => d.driver_id));
      setDriversInitialized(true);
    }
  }, [
    flow,
    sportKind,
    drivers,
    driversLoading,
    driversInitialized,
    driversRaceId,
    selectedRaceId,
  ]);

  const addOption = () => {
    setOptions([...options, ""]);
  };

  const removeOption = (index: number) => {
    if (options.length <= 2) return;
    setOptions(options.filter((_, i) => i !== index));
  };

  const updateOption = (index: number, value: string) => {
    const updated = [...options];
    updated[index] = value;
    setOptions(updated);
  };

  const rulesError = (() => {
    if (flow !== "custom" || step !== 2) return null;
    if (entryAmount < MIN_ENTRY || entryAmount > MAX_ENTRY) {
      return `Valor de entrada deve estar entre R$ ${MIN_ENTRY},00 e R$ ${MAX_ENTRY.toLocaleString("pt-BR")},00`;
    }
    if (
      maxParticipants < MIN_PARTICIPANTS ||
      maxParticipants > MAX_PARTICIPANTS
    ) {
      return `Número de participantes deve estar entre ${MIN_PARTICIPANTS} e ${MAX_PARTICIPANTS}`;
    }
    if (!closesAt) {
      return "Informe a data de encerramento";
    }
    if (new Date(closesAt) <= new Date()) {
      return "A data de encerramento deve ser no futuro";
    }
    return null;
  })();

  const sportRulesError = (() => {
    if (flow !== "sport" || step !== 3) return null;
    if (sportEntryAmount < MIN_ENTRY || sportEntryAmount > MAX_ENTRY) {
      return `Valor de entrada deve estar entre R$ ${MIN_ENTRY},00 e R$ ${MAX_ENTRY.toLocaleString("pt-BR")},00`;
    }
    if (
      sportMaxParticipants < MIN_PARTICIPANTS ||
      sportMaxParticipants > MAX_PARTICIPANTS
    ) {
      return `Número de participantes deve estar entre ${MIN_PARTICIPANTS} e ${MAX_PARTICIPANTS}`;
    }
    return null;
  })();

  const steps = flow === "sport" ? SPORT_STEPS : CUSTOM_STEPS;
  const loading = flow === "sport" ? sportCreateLoading : customLoading;
  const error = flow === "sport" ? sportCreateError : customError;

  const canAdvanceCustom = (): boolean => {
    switch (step) {
      case 0:
        return (
          title.trim().length >= 3 &&
          description.trim().length >= MIN_DESCRIPTION
        );
      case 1:
        return options.filter((o) => o.trim().length > 0).length >= 2;
      case 2:
        return rulesError === null;
      default:
        return true;
    }
  };

  const canAdvanceSport = (): boolean => {
    switch (step) {
      case 0:
        return (
          sportKind === "football" ||
          sportKind === "f1" ||
          sportKind === "tennis"
        );
      case 1:
        if (sportKind === "football") {
          return !!selectedLeagueId && !!selectedFixtureId;
        }
        if (sportKind === "f1") {
          return !!selectedRaceId;
        }
        return !!selectedTennisMatchId;
      case 2:
        if (sportKind === "football") {
          return !!selectedTemplate;
        }
        if (sportKind === "f1") {
          return (
            selectedTemplate === "f1_winner" &&
            selectedDriverIds.length >= MIN_DRIVERS &&
            selectedDriverIds.length <= MAX_DRIVERS
          );
        }
        return selectedTemplate === "tennis_winner";
      case 3:
        return sportRulesError === null;
      default:
        return true;
    }
  };

  const canAdvance = () =>
    flow === "sport" ? canAdvanceSport() : canAdvanceCustom();

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    if (step > 0) {
      setStep(step - 1);
    } else {
      resetFlow();
    }
  };

  const resetFlow = () => {
    setFlow("none");
    setStep(0);
    setSelectedLeagueId(null);
    setSelectedFixtureId(null);
    setSelectedRaceId(null);
    setSelectedDriverIds([]);
    setDriversInitialized(false);
    setSelectedTemplate("match_winner");
    setSelectedTennisMatchId(null);
    setSelectedTennisTour("ATP");
    dispatch(clearFixtures());
    dispatch(clearRaces());
    dispatch(clearDrivers());
    dispatch(clearTennisMatches());
  };

  const pickLeague = (leagueId: string) => {
    if (selectedLeagueId !== leagueId) {
      setSelectedLeagueId(leagueId);
      setSelectedFixtureId(null);
      dispatch(clearFixtures());
    }
  };

  const pickRace = (raceId: string) => {
    if (selectedRaceId !== raceId) {
      setSelectedRaceId(raceId);
      setSelectedDriverIds([]);
      setDriversInitialized(false);
      dispatch(clearDrivers());
    }
  };

  const pickSportKind = (kind: SportKind) => {
    if (sportKind === kind) return;
    setSportKind(kind);
    // Reset template + downstream picks so the new kind starts clean
    if (kind === "football") {
      setSelectedTemplate("match_winner");
    } else if (kind === "f1") {
      setSelectedTemplate("f1_winner");
    } else {
      setSelectedTemplate("tennis_winner");
    }
    setSelectedLeagueId(null);
    setSelectedFixtureId(null);
    setSelectedRaceId(null);
    setSelectedDriverIds([]);
    setDriversInitialized(false);
    setSelectedTennisMatchId(null);
    dispatch(clearFixtures());
    dispatch(clearRaces());
    dispatch(clearDrivers());
    dispatch(clearTennisMatches());
  };

  const pickTennisTour = (tour: TennisTour) => {
    if (selectedTennisTour === tour) return;
    setSelectedTennisTour(tour);
    setSelectedTennisMatchId(null);
    dispatch(clearTennisMatches());
  };

  const toggleDriver = (driverId: string) => {
    setSelectedDriverIds((prev) => {
      if (prev.includes(driverId)) {
        return prev.filter((id) => id !== driverId);
      }
      if (prev.length >= MAX_DRIVERS) {
        return prev;
      }
      return [...prev, driverId];
    });
  };

  const handleSubmitCustom = async () => {
    const filteredOptions = options
      .map((o) => o.trim())
      .filter((o) => o.length > 0);

    const result = await dispatch(
      createBet({
        title: title.trim(),
        description: description.trim() || undefined,
        category,
        options: filteredOptions,
        resolution_type: resolutionType,
        entry_amount: entryAmount,
        max_participants: maxParticipants,
        closes_at: new Date(closesAt).toISOString(),
        league_id: privateLeagueId || null,
      })
    );

    if (createBet.fulfilled.match(result)) {
      navigate(`/bets/${result.payload.id}`);
    }
  };

  const handleSubmitSport = async () => {
    if (sportKind === "football") {
      if (!selectedFixtureId) return;
      const result = await dispatch(
        createSportBet({
          template: selectedTemplate,
          fixture_id: selectedFixtureId,
          entry_amount: sportEntryAmount,
          max_participants: sportMaxParticipants,
          league_id: privateLeagueId || null,
        })
      );

      if (createSportBet.fulfilled.match(result)) {
        navigate(`/bets/${result.payload.id}`);
      }
      return;
    }

    if (sportKind === "f1") {
      if (!selectedRaceId) return;
      const driverNames = selectedDriverIds
        .map((id) => drivers.find((d) => d.driver_id === id)?.name)
        .filter((n): n is string => !!n);
      const result = await dispatch(
        createSportBet({
          template: "f1_winner",
          race_id: selectedRaceId,
          driver_names: driverNames,
          entry_amount: sportEntryAmount,
          max_participants: sportMaxParticipants,
          league_id: privateLeagueId || null,
        })
      );
      if (createSportBet.fulfilled.match(result)) {
        navigate(`/bets/${result.payload.id}`);
      }
      return;
    }

    if (sportKind === "tennis") {
      if (!selectedTennisMatchId) return;
      const result = await dispatch(
        createSportBet({
          template: "tennis_winner",
          tennis_match_id: selectedTennisMatchId,
          entry_amount: sportEntryAmount,
          max_participants: sportMaxParticipants,
          league_id: privateLeagueId || null,
        })
      );
      if (createSportBet.fulfilled.match(result)) {
        navigate(`/bets/${result.payload.id}`);
      }
    }
  };

  const handleSubmit = () =>
    flow === "sport" ? handleSubmitSport() : handleSubmitCustom();

  const formatCurrency = (val: number) =>
    `R$ ${val.toFixed(2).replace(".", ",")}`;

  // Options preview for the current sport template (used in steps 2 and 4)
  const sportOptionPreview: string[] = (() => {
    if (sportKind === "football" && selectedFixture) {
      if (selectedTemplate === "match_winner") {
        return [selectedFixture.home_team, "Empate", selectedFixture.away_team];
      }
      if (selectedTemplate === "exact_score") {
        return EXACT_SCORE_OPTIONS;
      }
      return [];
    }
    if (sportKind === "f1" && selectedTemplate === "f1_winner") {
      return selectedDriverIds
        .map((id) => drivers.find((d) => d.driver_id === id)?.name)
        .filter((n): n is string => !!n);
    }
    if (sportKind === "tennis" && selectedTennisMatch) {
      return [selectedTennisMatch.player1_name, selectedTennisMatch.player2_name];
    }
    return [];
  })();

  const sportEventDate: string | null = (() => {
    if (sportKind === "football" && selectedFixture) return selectedFixture.date;
    if (sportKind === "f1" && selectedRace) return selectedRace.date;
    if (sportKind === "tennis" && selectedTennisMatch)
      return selectedTennisMatch.date;
    return null;
  })();

  const sportEventTitle: string = (() => {
    if (sportKind === "football" && selectedFixture) {
      return `${selectedFixture.home_team} vs ${selectedFixture.away_team}`;
    }
    if (sportKind === "f1" && selectedRace) {
      const parts = [
        selectedRace.competition_name,
        selectedRace.circuit_name,
      ].filter(Boolean);
      return parts.join(" - ") || "Corrida";
    }
    if (sportKind === "tennis" && selectedTennisMatch) {
      return `${selectedTennisMatch.player1_name} vs ${selectedTennisMatch.player2_name}`;
    }
    return "-";
  })();

  // =================================================================
  // Render: type selector (shown when flow === "none")
  // =================================================================
  if (flow === "none") {
    return (
      <div className="create-bet-page">
        <h1 className="page-title">Criar Desafio</h1>
        <p className="form-hint">Escolha o tipo de desafio que quer criar:</p>

        <div className="bet-type-selector">
          <button
            type="button"
            className="bet-type-card card"
            onClick={() => {
              setFlow("sport");
              setStep(0);
            }}
          >
            <h3>Previsão Esportiva</h3>
            <p>
              Escolha uma partida ou corrida real e aposte no resultado.
              Resolução automática quando o evento terminar.
            </p>
          </button>

          <button
            type="button"
            className="bet-type-card card"
            onClick={() => {
              setFlow("custom");
              setStep(0);
            }}
          >
            <h3>Desafio Personalizado</h3>
            <p>
              Crie um desafio com suas próprias opções. Resolução por votação
              dos participantes.
            </p>
          </button>

          <button
            type="button"
            className="bet-type-card card bet-type-card-bolao"
            onClick={() => navigate("/bolao/create")}
          >
            <h3>Bolão da Copa do Mundo 2026</h3>
            <p>
              Palpite em todos os jogos da Copa. Pontuação dobrada nas
              eliminatórias + bônus de acertar o campeão. Ranking ao vivo,
              apuração automática.
            </p>
            <span className="bet-type-badge">Novo</span>
          </button>
        </div>
      </div>
    );
  }

  // =================================================================
  // Render: wizard (sport or custom)
  // =================================================================
  return (
    <div className="create-bet-page">
      <h1 className="page-title">
        {flow === "sport" ? "Nova Previsão Esportiva" : "Novo Desafio"}
      </h1>

      {/* Progress indicator */}
      <div className="step-progress">
        {steps.map((label, i) => (
          <div
            key={label}
            className={`step-item ${i === step ? "step-active" : ""} ${
              i < step ? "step-done" : ""
            }`}
          >
            <div className="step-circle">{i < step ? "OK" : i + 1}</div>
            <span className="step-label">{label}</span>
          </div>
        ))}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* ============================================================
          SPORT FLOW
         ============================================================ */}

      {/* Step 0: sport kind */}
      {flow === "sport" && step === 0 && (
        <div className="create-bet-form card">
          <p className="form-hint">Escolha o esporte:</p>
          <div className="sport-template-list">
            <button
              type="button"
              className={`sport-template-card ${
                sportKind === "football" ? "sport-template-card-active" : ""
              }`}
              onClick={() => pickSportKind("football")}
            >
              <h4>Futebol</h4>
              <p>
                Aposte no vencedor ou no placar exato de partidas das
                principais ligas.
              </p>
            </button>
            <button
              type="button"
              className={`sport-template-card ${
                sportKind === "f1" ? "sport-template-card-active" : ""
              }`}
              onClick={() => pickSportKind("f1")}
            >
              <h4>Fórmula 1</h4>
              <p>
                Aposte no piloto que vai vencer a próxima corrida do
                campeonato.
              </p>
            </button>
            {/* Tennis hidden until a real match-data provider is wired. */}
          </div>
        </div>
      )}

      {/* Step 1: evento (football = league + fixture; f1 = season + race) */}
      {flow === "sport" && step === 1 && sportKind === "football" && (
        <div className="create-bet-form card">
          <p className="form-hint">Escolha a liga ou competição:</p>
          {leaguesLoading && (
            <p className="form-hint">Carregando ligas...</p>
          )}
          {leaguesError && (
            <div className="alert alert-error">{leaguesError}</div>
          )}
          <div className="sport-league-list">
            {leagues.map((l) => (
              <button
                key={l.id}
                type="button"
                className={`sport-league-card ${
                  selectedLeagueId === l.id ? "sport-league-card-active" : ""
                }`}
                onClick={() => pickLeague(l.id)}
              >
                <span className="sport-league-name">{l.name}</span>
              </button>
            ))}
          </div>

          {selectedLeagueId && (
            <>
              <p className="form-hint" style={{ marginTop: "16px" }}>
                {selectedLeague
                  ? `Próximas partidas — ${selectedLeague.name}`
                  : "Escolha uma partida"}
              </p>
              {fixturesLoading && (
                <p className="form-hint">Carregando partidas...</p>
              )}
              {fixturesError && (
                <div className="alert alert-error">{fixturesError}</div>
              )}
              {!fixturesLoading &&
                !fixturesError &&
                fixtures.length === 0 &&
                selectedLeagueId && (
                  <div className="alert alert-info">
                    {fixturesReason === "api_key_missing"
                      ? "Integração esportiva ainda não configurada. Use desafio personalizado (votação) por enquanto."
                      : fixturesReason === "plan_limit"
                      ? "A integração esportiva atual está em plano gratuito e não inclui esta temporada. Use desafio personalizado (votação) por enquanto, ou contrate um plano pago do provedor de dados."
                      : fixturesReason === "all_finished"
                      ? "Esta temporada já terminou — todas as partidas foram disputadas. Escolha outra liga ou crie um desafio personalizado."
                      : fixturesReason === "upstream_error"
                      ? "Não conseguimos consultar as partidas agora. Tente outra liga ou tente de novo em alguns instantes."
                      : fixturesReason === "unknown_league"
                      ? "Liga não reconhecida. Escolha outra opção na lista."
                      : "Nenhuma partida agendada nesta liga. Tente outra liga ou crie um desafio personalizado."}
                  </div>
                )}
              <div className="sport-fixture-list">
                {fixtures.map((f) => (
                  <button
                    key={f.fixture_id}
                    type="button"
                    className={`sport-fixture-card ${
                      selectedFixtureId === f.fixture_id
                        ? "sport-fixture-card-active"
                        : ""
                    }`}
                    onClick={() => setSelectedFixtureId(f.fixture_id)}
                  >
                    <div className="sport-fixture-teams">
                      <div className="sport-fixture-team">
                        {f.home_logo && (
                          <img
                            src={f.home_logo}
                            alt={f.home_team}
                            className="sport-fixture-logo"
                          />
                        )}
                        <span>{f.home_team}</span>
                      </div>
                      <span className="sport-fixture-vs">vs</span>
                      <div className="sport-fixture-team">
                        {f.away_logo && (
                          <img
                            src={f.away_logo}
                            alt={f.away_team}
                            className="sport-fixture-logo"
                          />
                        )}
                        <span>{f.away_team}</span>
                      </div>
                    </div>
                    <div className="sport-fixture-date">
                      {formatFixtureDate(f.date)}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {flow === "sport" && step === 1 && sportKind === "f1" && (
        <div className="create-bet-form card">
          <div className="form-group">
            <label>Temporada</label>
            <select
              className="form-select"
              value={selectedSeason}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10);
                if (val !== selectedSeason) {
                  setSelectedSeason(val);
                  setSelectedRaceId(null);
                  setSelectedDriverIds([]);
                  setDriversInitialized(false);
                  dispatch(clearRaces());
                  dispatch(clearDrivers());
                }
              }}
            >
              {F1_SEASONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <p className="form-hint">Próximas corridas:</p>
          {racesLoading && <p className="form-hint">Carregando corridas...</p>}
          {racesError && <div className="alert alert-error">{racesError}</div>}
          {!racesLoading && !racesError && races.length === 0 && (
            <div className="alert alert-info">
              Nenhuma corrida futura encontrada nesta temporada.
            </div>
          )}
          <div className="sport-fixture-list">
            {races.map((r) => (
              <button
                key={r.race_id}
                type="button"
                className={`sport-fixture-card ${
                  selectedRaceId === r.race_id
                    ? "sport-fixture-card-active"
                    : ""
                }`}
                onClick={() => pickRace(r.race_id)}
              >
                <div className="sport-fixture-teams">
                  <div className="sport-fixture-team">
                    <span>{r.competition_name || "Corrida"}</span>
                  </div>
                </div>
                <div className="sport-fixture-date">
                  {r.circuit_name}
                  {r.circuit_location ? ` — ${r.circuit_location}` : ""}
                </div>
                <div className="sport-fixture-date">
                  {formatFixtureDate(r.date)}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {flow === "sport" && step === 1 && sportKind === "tennis" && (
        <div className="create-bet-form card">
          <div className="form-group">
            <label>Circuito</label>
            <div className="sport-template-list">
              <button
                type="button"
                className={`sport-template-card ${
                  selectedTennisTour === "ATP"
                    ? "sport-template-card-active"
                    : ""
                }`}
                onClick={() => pickTennisTour("ATP")}
              >
                <h4>ATP</h4>
                <p>Circuito masculino</p>
              </button>
              <button
                type="button"
                className={`sport-template-card ${
                  selectedTennisTour === "WTA"
                    ? "sport-template-card-active"
                    : ""
                }`}
                onClick={() => pickTennisTour("WTA")}
              >
                <h4>WTA</h4>
                <p>Circuito feminino</p>
              </button>
            </div>
          </div>

          <p className="form-hint">Próximas partidas:</p>
          {tennisMatchesLoading && (
            <p className="form-hint">Carregando partidas...</p>
          )}
          {tennisMatchesError && (
            <div className="alert alert-error">{tennisMatchesError}</div>
          )}
          {!tennisMatchesLoading &&
            !tennisMatchesError &&
            tennisMatches.length === 0 && (
              <div className="alert alert-info">
                Nenhuma partida futura encontrada neste circuito.
              </div>
            )}
          <div className="sport-fixture-list">
            {tennisMatches.map((m) => (
              <button
                key={m.match_id}
                type="button"
                className={`sport-fixture-card ${
                  selectedTennisMatchId === m.match_id
                    ? "sport-fixture-card-active"
                    : ""
                }`}
                onClick={() => setSelectedTennisMatchId(m.match_id)}
              >
                <div className="sport-fixture-teams">
                  <div className="sport-fixture-team">
                    <span>{m.player1_name}</span>
                  </div>
                  <span className="sport-fixture-vs">vs</span>
                  <div className="sport-fixture-team">
                    <span>{m.player2_name}</span>
                  </div>
                </div>
                <div className="sport-fixture-date">
                  {formatFixtureDate(m.date)}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step 2: aposta (template + F1 driver multi-select) */}
      {flow === "sport" && step === 2 && (
        <div className="create-bet-form card">
          <p className="form-hint">Escolha o tipo de aposta:</p>
          <div className="sport-template-list">
            {availableTemplates.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`sport-template-card ${
                  selectedTemplate === t.id ? "sport-template-card-active" : ""
                }`}
                onClick={() => setSelectedTemplate(t.id)}
              >
                <h4>{t.label}</h4>
                <p>{t.description}</p>
              </button>
            ))}
          </div>

          {sportKind === "football" && selectedFixture && (
            <div className="sport-options-preview">
              <span className="review-label">Opções geradas</span>
              <div className="review-options">
                {(selectedTemplate === "exact_score"
                  ? EXACT_SCORE_OPTIONS
                  : [
                      selectedFixture.home_team,
                      "Empate",
                      selectedFixture.away_team,
                    ]
                ).map((label) => (
                  <span key={label} className="review-option-tag">
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {sportKind === "f1" && (
            <div className="sport-options-preview">
              <span className="review-label">
                Pilotos ({selectedDriverIds.length}/{MAX_DRIVERS} — mín {MIN_DRIVERS})
              </span>
              {driversLoading && (
                <p className="form-hint">Carregando pilotos...</p>
              )}
              {driversError && (
                <div className="alert alert-error">{driversError}</div>
              )}
              {!driversLoading &&
                !driversError &&
                drivers.length === 0 && (
                  <div className="alert alert-info">
                    Nenhum piloto encontrado para esta corrida.
                  </div>
                )}
              <div className="sport-league-list">
                {drivers.map((d) => {
                  const selected = selectedDriverIds.includes(d.driver_id);
                  const atMax =
                    !selected && selectedDriverIds.length >= MAX_DRIVERS;
                  return (
                    <button
                      key={d.driver_id}
                      type="button"
                      className={`sport-league-card ${
                        selected ? "sport-league-card-active" : ""
                      }`}
                      onClick={() => toggleDriver(d.driver_id)}
                      disabled={atMax}
                    >
                      <span className="sport-league-name">
                        {d.name}
                        {d.team_name ? ` — ${d.team_name}` : ""}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Step 3: regras */}
      {flow === "sport" && step === 3 && (
        <div className="create-bet-form card">
          <div className="form-group">
            <label>Valor de entrada</label>
            <div className="input-with-prefix">
              <span className="input-prefix">R$</span>
              <input
                type="text"
                inputMode="decimal"
                placeholder="0,00"
                value={sportEntryAmountText}
                onChange={(e) => {
                  const v = e.target.value
                    .replace(",", ".")
                    .replace(/[^0-9.]/g, "");
                  setSportEntryAmountText(v);
                }}
              />
            </div>
            <span className="form-hint">
              Entre R$ {MIN_ENTRY},00 e R$ {MAX_ENTRY.toLocaleString("pt-BR")}
              ,00
            </span>
          </div>
          <div className="form-group">
            <label>Máximo de participantes</label>
            <input
              type="text"
              inputMode="numeric"
              placeholder="Ex: 20"
              value={sportMaxParticipantsText}
              onChange={(e) => {
                const v = e.target.value.replace(/[^0-9]/g, "");
                setSportMaxParticipantsText(v);
              }}
            />
            <span className="form-hint">
              Entre {MIN_PARTICIPANTS} e {MAX_PARTICIPANTS} participantes
            </span>
          </div>
          <div className="form-group">
            <label>Encerramento</label>
            <div className="form-readonly">
              {sportEventDate ? formatFixtureDate(sportEventDate) : "-"}
            </div>
            <span className="form-hint">
              Entradas fecham automaticamente no horário do evento
            </span>
          </div>
          <div className="form-group">
            <label>Criar dentro de uma liga? (opcional)</label>
            <select
              className="form-select"
              value={privateLeagueId}
              onChange={(e) => setPrivateLeagueId(e.target.value)}
            >
              <option value="">Nenhuma (aberto a qualquer convidado)</option>
              {myLeagues.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
            <span className="form-hint">
              Se escolher uma liga, apenas os membros verão este desafio na
              lista da liga
            </span>
          </div>
          {sportRulesError && (
            <div className="alert alert-error" style={{ marginTop: "8px" }}>
              {sportRulesError}
            </div>
          )}
        </div>
      )}

      {/* Step 4: revisão */}
      {flow === "sport" && step === 4 && (
        <div className="create-bet-form card">
          <h3>Resumo da previsão</h3>
          <div className="review-section">
            <div className="review-item">
              <span className="review-label">Esporte</span>
              <span className="review-value">
                {sportKind === "football"
                  ? "Futebol"
                  : sportKind === "f1"
                  ? "Fórmula 1"
                  : "Tênis"}
              </span>
            </div>
            {sportKind === "football" && (
              <div className="review-item">
                <span className="review-label">Liga</span>
                <span className="review-value">
                  {selectedLeague?.name || "-"}
                </span>
              </div>
            )}
            {sportKind === "f1" && (
              <div className="review-item">
                <span className="review-label">Temporada</span>
                <span className="review-value">{selectedSeason}</span>
              </div>
            )}
            {sportKind === "tennis" && (
              <div className="review-item">
                <span className="review-label">Circuito</span>
                <span className="review-value">{selectedTennisTour}</span>
              </div>
            )}
            <div className="review-item">
              <span className="review-label">
                {sportKind === "football"
                  ? "Partida"
                  : sportKind === "f1"
                  ? "Corrida"
                  : "Partida"}
              </span>
              <span className="review-value">{sportEventTitle}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Data do evento</span>
              <span className="review-value">
                {sportEventDate ? formatFixtureDate(sportEventDate) : "-"}
              </span>
            </div>
            <div className="review-item">
              <span className="review-label">Tipo de aposta</span>
              <span className="review-value">
                {selectedTemplateData?.label || "-"}
              </span>
            </div>
            <div className="review-item">
              <span className="review-label">Opções</span>
              <div className="review-options">
                {sportOptionPreview.map((label) => (
                  <span key={label} className="review-option-tag">
                    {label}
                  </span>
                ))}
              </div>
            </div>
            <div className="review-item">
              <span className="review-label">Entrada</span>
              <span className="review-value">
                {formatCurrency(sportEntryAmount)}
              </span>
            </div>
            <div className="review-item">
              <span className="review-label">Max. participantes</span>
              <span className="review-value">{sportMaxParticipants}</span>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================
          CUSTOM FLOW (unchanged behaviour)
         ============================================================ */}
      {flow === "custom" && step === 0 && (
        <div className="create-bet-form card">
          <div className="form-group">
            <label>Título do desafio</label>
            <input
              type="text"
              placeholder="Ex: Quem ganha o clássico?"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={100}
            />
          </div>
          <div className="form-group">
            <label>Regulamento do desafio</label>
            <textarea
              className="form-textarea"
              placeholder="Descreva as regras: como a vitória é definida, o que conta como empate, prazo, critérios de desempate, etc. Os convidados terão que aceitar esse regulamento antes de participar."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={6}
              maxLength={2000}
            />
            <span className="form-hint">
              Obrigatório — mínimo {MIN_DESCRIPTION} caracteres. Escreva com
              clareza: esse texto aparece para todos os convidados e é a base
              da apuração por votação.
              {description.trim().length > 0 &&
                description.trim().length < MIN_DESCRIPTION && (
                  <>
                    {" "}
                    Faltam {MIN_DESCRIPTION - description.trim().length}{" "}
                    caracteres.
                  </>
                )}
            </span>
          </div>
        </div>
      )}

      {flow === "custom" && step === 1 && (
        <div className="create-bet-form card">
          <p className="form-hint">
            Adicione pelo menos 2 opções para o desafio.
          </p>
          {options.map((opt, i) => (
            <div key={i} className="option-row">
              <div className="form-group option-input-group">
                <label>Opção {i + 1}</label>
                <input
                  type="text"
                  placeholder={`Opção ${i + 1}`}
                  value={opt}
                  onChange={(e) => updateOption(i, e.target.value)}
                  maxLength={100}
                />
              </div>
              {options.length > 2 && (
                <button
                  type="button"
                  className="btn btn-secondary btn-remove-option"
                  onClick={() => removeOption(i)}
                >
                  Remover
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            className="btn btn-secondary btn-full"
            onClick={addOption}
          >
            Adicionar opção
          </button>
        </div>
      )}

      {flow === "custom" && step === 2 && (
        <div className="create-bet-form card">
          <div className="form-group">
            <label>Valor de entrada</label>
            <div className="input-with-prefix">
              <span className="input-prefix">R$</span>
              <input
                type="text"
                inputMode="decimal"
                placeholder="0,00"
                value={entryAmountText}
                onChange={(e) => {
                  const v = e.target.value
                    .replace(",", ".")
                    .replace(/[^0-9.]/g, "");
                  setEntryAmountText(v);
                }}
              />
            </div>
            <span className="form-hint">
              Entre R$ {MIN_ENTRY},00 e R$ {MAX_ENTRY.toLocaleString("pt-BR")}
              ,00
            </span>
          </div>
          <div className="form-group">
            <label>Máximo de participantes</label>
            <input
              type="text"
              inputMode="numeric"
              placeholder="Ex: 20"
              value={maxParticipantsText}
              onChange={(e) => {
                const v = e.target.value.replace(/[^0-9]/g, "");
                setMaxParticipantsText(v);
              }}
            />
            <span className="form-hint">
              Entre {MIN_PARTICIPANTS} e {MAX_PARTICIPANTS} participantes
            </span>
          </div>
          <div className="form-group">
            <label>Data e hora de encerramento</label>
            <input
              type="datetime-local"
              className="form-datetime"
              value={closesAt}
              onChange={(e) => setClosesAt(e.target.value)}
              min={new Date().toISOString().slice(0, 16)}
            />
            <span className="form-hint">
              Após esta data, novas participações não são aceitas
            </span>
          </div>
          <div className="form-group">
            <label>Criar dentro de uma liga? (opcional)</label>
            <select
              className="form-select"
              value={privateLeagueId}
              onChange={(e) => setPrivateLeagueId(e.target.value)}
            >
              <option value="">Nenhuma (aberto a qualquer convidado)</option>
              {myLeagues.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
            <span className="form-hint">
              Se escolher uma liga, apenas os membros verão este desafio na
              lista da liga
            </span>
          </div>
          {rulesError && (
            <div className="alert alert-error" style={{ marginTop: "8px" }}>
              {rulesError}
            </div>
          )}
        </div>
      )}

      {flow === "custom" && step === 3 && (
        <div className="create-bet-form card">
          <h3>Resumo do desafio</h3>
          <div className="review-section">
            <div className="review-item">
              <span className="review-label">Título</span>
              <span className="review-value">{title}</span>
            </div>
            {description && (
              <div className="review-item">
                <span className="review-label">Regulamento</span>
                <span className="review-value review-regulamento">
                  {description}
                </span>
              </div>
            )}
            <div className="review-item">
              <span className="review-label">Opções</span>
              <div className="review-options">
                {options
                  .filter((o) => o.trim())
                  .map((o, i) => (
                    <span key={i} className="review-option-tag">
                      {o}
                    </span>
                  ))}
              </div>
            </div>
            <div className="review-item">
              <span className="review-label">Resolução</span>
              <span className="review-value">
                {resolutionType === "voting" ? "Votação" : "Automático (API)"}
              </span>
            </div>
            <div className="review-item">
              <span className="review-label">Entrada</span>
              <span className="review-value">
                {formatCurrency(entryAmount)}
              </span>
            </div>
            <div className="review-item">
              <span className="review-label">Max. participantes</span>
              <span className="review-value">{maxParticipants}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Encerramento</span>
              <span className="review-value">
                {closesAt ? new Date(closesAt).toLocaleString("pt-BR") : "-"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Navigation buttons */}
      <div className="step-nav">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleBack}
        >
          {step === 0 ? "Trocar tipo" : "Voltar"}
        </button>
        {step < steps.length - 1 ? (
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleNext}
            disabled={!canAdvance()}
          >
            Próximo
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading
              ? "Criando..."
              : flow === "sport"
                ? "Criar Previsão"
                : "Criar Desafio"}
          </button>
        )}
      </div>
    </div>
  );
}
