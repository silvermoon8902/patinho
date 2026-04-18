import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import type { RootState, AppDispatch } from "@/store";
import { fetchFeeConfig, updateFeeConfig } from "@/store/adminSlice";

function formatFeePreview(feeType: string, feeValue: number): string {
  if (feeType === "percent") {
    return `Taxa atual: ${feeValue}% sobre o pote`;
  }
  const formatted = feeValue.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
  return `Taxa atual: ${formatted} por desafio`;
}

export default function AdminFeePage() {
  const dispatch = useDispatch<AppDispatch>();
  const { feeConfig, loading, error } = useSelector(
    (state: RootState) => state.admin
  );
  const [feeType, setFeeType] = useState<string>("percent");
  const [feeValue, setFeeValue] = useState<string>("8");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    dispatch(fetchFeeConfig());
  }, [dispatch]);

  useEffect(() => {
    if (feeConfig) {
      setFeeType(feeConfig.fee_type);
      setFeeValue(String(feeConfig.fee_value));
    }
  }, [feeConfig]);

  function handleSave() {
    const numValue = parseFloat(feeValue);
    if (isNaN(numValue) || numValue < 0) return;
    dispatch(updateFeeConfig({ fee_type: feeType, fee_value: numValue })).then(
      (result) => {
        if (updateFeeConfig.fulfilled.match(result)) {
          setSaved(true);
          setTimeout(() => setSaved(false), 3000);
        }
      }
    );
  }

  const numPreview = parseFloat(feeValue) || 0;

  return (
    <div className="admin-page">
      <h1 className="admin-page-title">Configuracao de Taxa</h1>

      {error && <div className="alert alert-error">{error}</div>}
      {saved && (
        <div className="alert alert-success">Taxa atualizada com sucesso</div>
      )}

      {loading && !feeConfig && (
        <p className="empty-state">Carregando...</p>
      )}

      <div className="admin-fee-form card">
        <h3>Tipo de Taxa</h3>

        <div className="admin-fee-radio-group">
          <label className="admin-radio-label">
            <input
              type="radio"
              name="fee_type"
              value="percent"
              checked={feeType === "percent"}
              onChange={() => setFeeType("percent")}
            />
            Porcentagem (%)
          </label>
          <label className="admin-radio-label">
            <input
              type="radio"
              name="fee_type"
              value="fixed"
              checked={feeType === "fixed"}
              onChange={() => setFeeType("fixed")}
            />
            Valor fixo (R$)
          </label>
        </div>

        <div className="form-group">
          <label>
            {feeType === "percent"
              ? "Porcentagem da taxa"
              : "Valor fixo da taxa (R$)"}
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={feeValue}
            onChange={(e) => setFeeValue(e.target.value)}
          />
        </div>

        <div className="admin-fee-preview">
          {formatFeePreview(feeType, numPreview)}
        </div>

        <button className="btn btn-primary btn-full" onClick={handleSave}>
          Salvar Configuracao
        </button>
      </div>
    </div>
  );
}
