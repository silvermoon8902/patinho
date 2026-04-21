import { useState } from "react";
import { useDispatch } from "react-redux";
import type { AppDispatch } from "@/store";
import { joinLeague } from "@/store/leaguesSlice";
import { useToast } from "@/components/shared/Toast";

interface Props {
  open: boolean;
  onClose: () => void;
  onJoined?: (leagueId: string) => void;
}

export default function JoinByCodeModal({ open, onClose, onJoined }: Props) {
  const dispatch = useDispatch<AppDispatch>();
  const { showToast } = useToast();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const handleClose = () => {
    setCode("");
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = code.trim();
    if (trimmed.length < 3) {
      showToast("Digite um código de convite válido", "error");
      return;
    }
    setLoading(true);
    const result = await dispatch(joinLeague({ inviteCode: trimmed }));
    setLoading(false);

    if (joinLeague.fulfilled.match(result)) {
      showToast("Você entrou na liga", "success");
      const leagueId = result.payload.id;
      setCode("");
      onClose();
      onJoined?.(leagueId);
    } else {
      showToast(
        (result.payload as string) || "Erro ao entrar na liga",
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
        <h2>Entrar com código de convite</h2>
        <p className="league-modal-subtitle">
          Digite o código que um amigo compartilhou com você.
        </p>

        <form onSubmit={handleSubmit} className="league-form">
          <div className="form-group">
            <label htmlFor="join-code">Código de convite</label>
            <input
              id="join-code"
              type="text"
              className="form-input league-code-input"
              maxLength={12}
              minLength={3}
              required
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Ex: a1B2c3D4e"
            />
          </div>

          <div className="league-modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleClose}
              disabled={loading}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? "Entrando..." : "Entrar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
