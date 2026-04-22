import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import { createLeague, clearLeagueError } from "@/store/leaguesSlice";
import { useToast } from "@/components/shared/Toast";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated?: (leagueId: string) => void;
}

export default function CreateLeagueModal({ open, onClose, onCreated }: Props) {
  const dispatch = useDispatch<AppDispatch>();
  const { showToast } = useToast();
  const { createLoading, createError } = useSelector(
    (state: RootState) => state.leagues
  );

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  if (!open) return null;

  const handleClose = () => {
    setName("");
    setDescription("");
    dispatch(clearLeagueError());
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim().length < 3) {
      showToast("O nome da liga deve ter ao menos 3 caracteres", "error");
      return;
    }

    const result = await dispatch(
      createLeague({
        name: name.trim(),
        description: description.trim() || undefined,
      })
    );

    if (createLeague.fulfilled.match(result)) {
      showToast("Liga criada com sucesso", "success");
      const leagueId = result.payload.id;
      setName("");
      setDescription("");
      onClose();
      onCreated?.(leagueId);
    } else {
      showToast(
        (result.payload as string) || "Erro ao criar liga",
        "error"
      );
    }
  };

  return (
    <div
      className="league-modal-overlay"
      role="dialog"
      aria-modal="true"
      onClick={handleClose}
    >
      <div
        className="card league-modal-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Criar nova liga</h2>
        <p className="league-modal-subtitle">
          Reúna seus amigos em um grupo para criar desafios e previsões juntos.
        </p>

        <form onSubmit={handleSubmit} className="league-form">
          <div className="form-group">
            <label htmlFor="league-name">Nome da liga</label>
            <input
              id="league-name"
              type="text"
              className="form-input"
              maxLength={80}
              minLength={3}
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex: Galera do Futebol"
            />
          </div>

          <div className="form-group">
            <label htmlFor="league-description">
              Descrição (opcional)
            </label>
            <textarea
              id="league-description"
              className="form-input"
              maxLength={500}
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Do que vocês costumam apostar?"
            />
          </div>

          {createError && (
            <div className="alert alert-error">{createError}</div>
          )}

          <div className="league-modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleClose}
              disabled={createLoading}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createLoading}
            >
              {createLoading ? "Criando..." : "Criar liga"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
