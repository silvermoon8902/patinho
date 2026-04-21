import { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/store";
import {
  inviteToLeague,
  resetInviteStatus,
  fetchLeagueDetail,
} from "@/store/leaguesSlice";
import { useToast } from "@/components/shared/Toast";

interface Props {
  open: boolean;
  leagueId: string;
  onClose: () => void;
}

export default function InviteMemberModal({ open, leagueId, onClose }: Props) {
  const dispatch = useDispatch<AppDispatch>();
  const { showToast } = useToast();
  const inviteStatus = useSelector(
    (state: RootState) => state.leagues.inviteStatus
  );
  const [identifier, setIdentifier] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) {
      dispatch(resetInviteStatus());
      setIdentifier("");
    }
  }, [open, dispatch]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (identifier.trim().length < 3) {
      showToast("Digite um nome de usuário ou email válido", "error");
      return;
    }
    setLoading(true);
    const result = await dispatch(
      inviteToLeague({ leagueId, identifier: identifier.trim() })
    );
    setLoading(false);

    if (inviteToLeague.fulfilled.match(result)) {
      const status = result.payload?.status;
      if (status === "added") {
        showToast("Usuário adicionado à liga", "success");
        await dispatch(fetchLeagueDetail(leagueId));
        setIdentifier("");
        onClose();
      } else if (status === "already_member") {
        showToast("Esse usuário já é membro da liga", "info");
      } else if (status === "user_not_found") {
        showToast("Usuário não encontrado", "error");
      } else {
        showToast("Não foi possível convidar", "error");
      }
    } else {
      showToast(
        (result.payload as string) || "Erro ao convidar",
        "error"
      );
    }
  };

  return (
    <div
      className="league-modal-overlay"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="card league-modal-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Convidar amigo</h2>
        <p className="league-modal-subtitle">
          Use o nome de usuário ou o email de um amigo já cadastrado.
        </p>

        <form onSubmit={handleSubmit} className="league-form">
          <div className="form-group">
            <label htmlFor="invite-identifier">
              Usuário ou email
            </label>
            <input
              id="invite-identifier"
              type="text"
              className="form-input"
              maxLength={100}
              minLength={3}
              required
              autoFocus
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="nome_de_usuario ou email@dominio.com"
            />
          </div>

          {inviteStatus === "notfound" && (
            <div className="alert alert-error">
              Usuário não encontrado. Ele precisa ter uma conta no Patinho.
            </div>
          )}
          {inviteStatus === "already" && (
            <div className="alert alert-info">
              Esse usuário já é membro da liga.
            </div>
          )}

          <div className="league-modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Fechar
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? "Enviando..." : "Convidar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
