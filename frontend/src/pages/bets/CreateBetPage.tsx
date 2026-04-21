import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { createBet } from "@/store/betSlice";
import {
  clearFixtures,
  createSportBet,
  fetchFixtures,
  fetchLeagues,
} from "@/store/sportsSlice";

const CATEGORIES = [
  { value: "football", label: "Futebol" },
  { value: "f1", label: "F1" },
  { value: "tennis", label: "Tênis" },
  { value: "bbb", label: "BBB" },
  { value: "politics", label: "Política" },
  { value: "custom", label: "Outro" },
];

type BetFlow = "none" | "sport" | "custom";

const CUSTOM_STEPS = ["Informações", "Opções", "Regras", "Revisão"];
const SPORT_STEPS = ["Liga", "Partida", "Aposta", "Regras", "Revisão"];

const MIN_ENTRY = 5;
const MAX_ENTRY = 1000;
const MIN_PARTICIPANTS = 2;
const MAX_PARTICIPANTS = 100;

const SPORT_TEMPLATES = [
  {
    id: "match_winner",
    label: "Quem vence?",
    description: "Escolha o vencedor da partida (ou empate)",
  },
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
  const {
    leagues,
    leaguesLoading,
    leaguesError,
    fixtures,
    fixturesLoading,
    fixturesError,
    fixturesLeagueId,
    createLoading: sportCreateLoading,
    createError: sportCreateError,
  } = useSelector((state: RootState) => state.sports);

  const [flow, setFlow] = useState<BetFlow>("none");
  const [step, setStep] = useState(0);

  // Custom flow state
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("football");
  const [options, setOptions] = useState(["", ""]);
  const [resolutionType, setResolutionType] = useState<"auto_api" | "voting">(
    "voting"
  );
  const [entryAmountText, setEntryAmountText] = useState(String(MIN_ENTRY));
  const [maxParticipantsText, setMaxParticipantsText] = useState("100");
  const [closesAt, setClosesAt] = useState("");

  // Sport flow state
  const [selectedLeagueId, setSelectedLeagueId] = useState<string | null>(null);
  const [selectedFixtureId, setSelectedFixtureId] = useState<string | null>(
    null
  );
  const [selectedTemplate, setSelectedTemplate] = useState<string>(
    SPORT_TEMPLATES[0]!.id
  );
  const [sportEntryAmountText, setSportEntryAmountText] = useState(
    String(MIN_ENTRY)
  );
  const [sportMaxParticipantsText, setSportMaxParticipantsText] =
    useState("100");

  const entryAmount = parseFloat(entryAmountText) || 0;
  const maxParticipants = parseInt(maxParticipantsText) || 0;
  const sportEntryAmount = parseFloat(sportEntryAmountText) || 0;
  const sportMaxParticipants = parseInt(sportMaxParticipantsText) || 0;

  const selectedLeague = leagues.find((l) => l.id === selectedLeagueId) || null;
  const selectedFixture =
    fixtures.find((f) => f.fixture_id === selectedFixtureId) || null;

  // Fetch leagues when user enters the sport flow (step 0 of sport).
  useEffect(() => {
    if (flow === "sport" && leagues.length === 0 && !leaguesLoading) {
      dispatch(fetchLeagues());
    }
  }, [flow, leagues.length, leaguesLoading, dispatch]);

  // Fetch fixtures when user lands on step 1 (Partida) with a league picked
  // and the cached fixtures don't match the currently selected league.
  useEffect(() => {
    if (
      flow === "sport" &&
      step === 1 &&
      selectedLeagueId &&
      !fixturesLoading &&
      fixturesLeagueId !== selectedLeagueId
    ) {
      dispatch(fetchFixtures({ leagueId: selectedLeagueId }));
    }
  }, [flow, step, selectedLeagueId, fixturesLoading, fixturesLeagueId, dispatch]);

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
        return title.trim().length >= 3;
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
        return !!selectedLeagueId;
      case 1:
        return !!selectedFixtureId;
      case 2:
        return !!selectedTemplate;
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
      // Back from first step returns to type selector
      resetFlow();
    }
  };

  const resetFlow = () => {
    setFlow("none");
    setStep(0);
    setSelectedLeagueId(null);
    setSelectedFixtureId(null);
    dispatch(clearFixtures());
  };

  const pickLeague = (leagueId: string) => {
    if (selectedLeagueId !== leagueId) {
      setSelectedLeagueId(leagueId);
      setSelectedFixtureId(null);
      dispatch(clearFixtures());
    }
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
      })
    );

    if (createBet.fulfilled.match(result)) {
      navigate(`/bets/${result.payload.id}`);
    }
  };

  const handleSubmitSport = async () => {
    if (!selectedFixtureId) return;
    const result = await dispatch(
      createSportBet({
        fixture_id: selectedFixtureId,
        template: selectedTemplate,
        entry_amount: sportEntryAmount,
        max_participants: sportMaxParticipants,
      })
    );

    if (createSportBet.fulfilled.match(result)) {
      navigate(`/bets/${result.payload.id}`);
    }
  };

  const handleSubmit = () =>
    flow === "sport" ? handleSubmitSport() : handleSubmitCustom();

  const getCategoryLabel = (val: string) =>
    CATEGORIES.find((c) => c.value === val)?.label || val;

  const formatCurrency = (val: number) =>
    `R$ ${val.toFixed(2).replace(".", ",")}`;

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
            <div className="bet-type-icon">⚽</div>
            <h3>Previsão Esportiva</h3>
            <p>
              Escolha uma partida real e aposte no vencedor. Resolução
              automática quando o jogo terminar.
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
            <div className="bet-type-icon">🎯</div>
            <h3>Desafio Personalizado</h3>
            <p>
              Crie um desafio com suas próprias opções. Resolução por votação
              dos participantes.
            </p>
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
            <div className="step-circle">{i < step ? "✓" : i + 1}</div>
            <span className="step-label">{label}</span>
          </div>
        ))}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* ============================================================
          SPORT FLOW
         ============================================================ */}
      {flow === "sport" && step === 0 && (
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
        </div>
      )}

      {flow === "sport" && step === 1 && (
        <div className="create-bet-form card">
          <p className="form-hint">
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
          {!fixturesLoading && !fixturesError && fixtures.length === 0 && (
            <div className="alert alert-info">
              Nenhuma partida futura encontrada para esta liga.
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
        </div>
      )}

      {flow === "sport" && step === 2 && (
        <div className="create-bet-form card">
          <p className="form-hint">Escolha o tipo de aposta:</p>
          <div className="sport-template-list">
            {SPORT_TEMPLATES.map((t) => (
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
          {selectedFixture && (
            <div className="sport-options-preview">
              <span className="review-label">Opções geradas</span>
              <div className="review-options">
                <span className="review-option-tag">
                  {selectedFixture.home_team}
                </span>
                <span className="review-option-tag">Empate</span>
                <span className="review-option-tag">
                  {selectedFixture.away_team}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

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
              {selectedFixture
                ? formatFixtureDate(selectedFixture.date)
                : "-"}
            </div>
            <span className="form-hint">
              Entradas fecham automaticamente no horário do jogo
            </span>
          </div>
          {sportRulesError && (
            <div className="alert alert-error" style={{ marginTop: "8px" }}>
              {sportRulesError}
            </div>
          )}
        </div>
      )}

      {flow === "sport" && step === 4 && (
        <div className="create-bet-form card">
          <h3>Resumo da previsão</h3>
          <div className="review-section">
            <div className="review-item">
              <span className="review-label">Liga</span>
              <span className="review-value">
                {selectedLeague?.name || "-"}
              </span>
            </div>
            <div className="review-item">
              <span className="review-label">Partida</span>
              <span className="review-value">
                {selectedFixture
                  ? `${selectedFixture.home_team} vs ${selectedFixture.away_team}`
                  : "-"}
              </span>
            </div>
            <div className="review-item">
              <span className="review-label">Data do jogo</span>
              <span className="review-value">
                {selectedFixture
                  ? formatFixtureDate(selectedFixture.date)
                  : "-"}
              </span>
            </div>
            <div className="review-item">
              <span className="review-label">Tipo de aposta</span>
              <span className="review-value">
                {SPORT_TEMPLATES.find((t) => t.id === selectedTemplate)
                  ?.label || "-"}
              </span>
            </div>
            <div className="review-item">
              <span className="review-label">Opções</span>
              <div className="review-options">
                {selectedFixture && (
                  <>
                    <span className="review-option-tag">
                      {selectedFixture.home_team}
                    </span>
                    <span className="review-option-tag">Empate</span>
                    <span className="review-option-tag">
                      {selectedFixture.away_team}
                    </span>
                  </>
                )}
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
            <label>Descrição (opcional)</label>
            <textarea
              className="form-textarea"
              placeholder="Descreva os detalhes do desafio..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              maxLength={500}
            />
          </div>
          <div className="form-group">
            <label>Categoria</label>
            <select
              className="form-select"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
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
            <label>Tipo de resolução</label>
            <select
              className="form-select"
              value={resolutionType}
              onChange={(e) =>
                setResolutionType(e.target.value as "auto_api" | "voting")
              }
            >
              <option value="voting">Votação (Desafio Personalizado)</option>
              <option value="auto_api">Automático (Previsão Esportiva)</option>
            </select>
          </div>
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
                <span className="review-label">Descrição</span>
                <span className="review-value">{description}</span>
              </div>
            )}
            <div className="review-item">
              <span className="review-label">Categoria</span>
              <span className="review-value">{getCategoryLabel(category)}</span>
            </div>
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
