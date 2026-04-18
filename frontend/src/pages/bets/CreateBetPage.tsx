import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { createBet } from "@/store/betSlice";

const CATEGORIES = [
  { value: "football", label: "Futebol" },
  { value: "f1", label: "F1" },
  { value: "tennis", label: "Tenis" },
  { value: "bbb", label: "BBB" },
  { value: "politics", label: "Politica" },
  { value: "custom", label: "Outro" },
];

const STEPS = ["Informacoes", "Opcoes", "Regras", "Revisao"];

const MIN_ENTRY = 5;
const MAX_ENTRY = 1000;

export default function CreateBetPage() {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { loading, error } = useSelector((state: RootState) => state.bets);

  const [step, setStep] = useState(0);

  // Step 1: Basic info
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("football");

  // Step 2: Options
  const [options, setOptions] = useState(["", ""]);

  // Step 3: Rules
  const [resolutionType, setResolutionType] = useState<"auto_api" | "voting">("voting");
  const [entryAmount, setEntryAmount] = useState(MIN_ENTRY);
  const [maxParticipants, setMaxParticipants] = useState(100);
  const [closesAt, setClosesAt] = useState("");

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

  const canAdvance = (): boolean => {
    switch (step) {
      case 0:
        return title.trim().length >= 3;
      case 1:
        return (
          options.filter((o) => o.trim().length > 0).length >= 2
        );
      case 2:
        return closesAt.length > 0 && entryAmount >= MIN_ENTRY && entryAmount <= MAX_ENTRY;
      default:
        return true;
    }
  };

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    if (step > 0) {
      setStep(step - 1);
    }
  };

  const handleSubmit = async () => {
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

  const getCategoryLabel = (val: string) =>
    CATEGORIES.find((c) => c.value === val)?.label || val;

  const formatCurrency = (val: number) =>
    `R$ ${val.toFixed(2).replace(".", ",")}`;

  return (
    <div className="create-bet-page">
      <h1 className="page-title">Criar Desafio</h1>

      {/* Progress indicator */}
      <div className="step-progress">
        {STEPS.map((label, i) => (
          <div
            key={label}
            className={`step-item ${i === step ? "step-active" : ""} ${
              i < step ? "step-done" : ""
            }`}
          >
            <div className="step-circle">{i < step ? "\u2713" : i + 1}</div>
            <span className="step-label">{label}</span>
          </div>
        ))}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Step 1: Basic info */}
      {step === 0 && (
        <div className="create-bet-form card">
          <div className="form-group">
            <label>Titulo do desafio</label>
            <input
              type="text"
              placeholder="Ex: Quem ganha o classico?"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={100}
            />
          </div>
          <div className="form-group">
            <label>Descricao (opcional)</label>
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

      {/* Step 2: Options */}
      {step === 1 && (
        <div className="create-bet-form card">
          <p className="form-hint">
            Adicione pelo menos 2 opcoes para o desafio.
          </p>
          {options.map((opt, i) => (
            <div key={i} className="option-row">
              <div className="form-group option-input-group">
                <label>Opcao {i + 1}</label>
                <input
                  type="text"
                  placeholder={`Opcao ${i + 1}`}
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
            Adicionar opcao
          </button>
        </div>
      )}

      {/* Step 3: Rules */}
      {step === 2 && (
        <div className="create-bet-form card">
          <div className="form-group">
            <label>Tipo de resolucao</label>
            <select
              className="form-select"
              value={resolutionType}
              onChange={(e) =>
                setResolutionType(e.target.value as "auto_api" | "voting")
              }
            >
              <option value="voting">Votacao (Desafio Personalizado)</option>
              <option value="auto_api">Automatico (Previsao Esportiva)</option>
            </select>
          </div>
          <div className="form-group">
            <label>Valor de entrada (R$)</label>
            <input
              type="number"
              min={MIN_ENTRY}
              max={MAX_ENTRY}
              value={entryAmount}
              onChange={(e) => setEntryAmount(Number(e.target.value))}
            />
          </div>
          <div className="form-group">
            <label>Maximo de participantes</label>
            <input
              type="number"
              min={2}
              max={1000}
              value={maxParticipants}
              onChange={(e) => setMaxParticipants(Number(e.target.value))}
            />
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
          </div>
        </div>
      )}

      {/* Step 4: Review */}
      {step === 3 && (
        <div className="create-bet-form card">
          <h3>Resumo do desafio</h3>
          <div className="review-section">
            <div className="review-item">
              <span className="review-label">Titulo</span>
              <span className="review-value">{title}</span>
            </div>
            {description && (
              <div className="review-item">
                <span className="review-label">Descricao</span>
                <span className="review-value">{description}</span>
              </div>
            )}
            <div className="review-item">
              <span className="review-label">Categoria</span>
              <span className="review-value">{getCategoryLabel(category)}</span>
            </div>
            <div className="review-item">
              <span className="review-label">Opcoes</span>
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
              <span className="review-label">Resolucao</span>
              <span className="review-value">
                {resolutionType === "voting" ? "Votacao" : "Automatico (API)"}
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
                {closesAt
                  ? new Date(closesAt).toLocaleString("pt-BR")
                  : "-"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Navigation buttons */}
      <div className="step-nav">
        {step > 0 && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleBack}
          >
            Voltar
          </button>
        )}
        {step < STEPS.length - 1 ? (
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleNext}
            disabled={!canAdvance()}
          >
            Proximo
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? "Criando..." : "Criar Desafio"}
          </button>
        )}
      </div>
    </div>
  );
}
