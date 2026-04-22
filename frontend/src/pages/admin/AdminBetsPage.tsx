import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import type { RootState, AppDispatch } from "@/store";
import {
  fetchAdminBets,
  forceResolveBet,
  forceCancelBet,
} from "@/store/adminSlice";
import type { AdminBet } from "@/store/adminSlice";
import { formatCurrency } from "@/utils/format";
import { SkeletonListRow } from "@/components/shared/Skeleton";

const STATUS_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "open", label: "Aberta" },
  { value: "locked", label: "Travada" },
  { value: "voting", label: "Votação" },
  { value: "disputed", label: "Disputada" },
  { value: "resolved", label: "Resolvida" },
  { value: "cancelled", label: "Cancelada" },
];

const STATUS_LABELS: Record<string, string> = {
  draft: "Rascunho",
  open: "Aberta",
  locked: "Travada",
  voting: "Votação",
  disputed: "Disputada",
  resolved: "Resolvida",
  cancelled: "Cancelada",
};

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("pt-BR");
}

export default function AdminBetsPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { bets, loading, error } = useSelector(
    (state: RootState) => state.admin
  );
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [resolveModal, setResolveModal] = useState<AdminBet | null>(null);
  const [selectedOptionId, setSelectedOptionId] = useState<string>("");
  const [confirmCancelId, setConfirmCancelId] = useState<string | null>(null);

  useEffect(() => {
    dispatch(
      fetchAdminBets({ status: statusFilter || undefined, page })
    );
  }, [dispatch, statusFilter, page]);

  function handleStatusChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setStatusFilter(e.target.value);
    setPage(1);
  }

  function openResolveModal(bet: AdminBet) {
    setResolveModal(bet);
    setSelectedOptionId(bet.options.length > 0 ? bet.options[0].id : "");
  }

  function handleForceResolve() {
    if (!resolveModal || !selectedOptionId) return;
    dispatch(
      forceResolveBet({
        betId: resolveModal.id,
        winningOptionId: selectedOptionId,
      })
    );
    setResolveModal(null);
    setSelectedOptionId("");
  }

  function handleForceCancel(betId: string) {
    dispatch(forceCancelBet(betId));
    setConfirmCancelId(null);
  }

  const canAct = (status: string) =>
    !["resolved", "cancelled"].includes(status);

  return (
    <div className="admin-page">
      <h1 className="admin-page-title">Gerenciar Desafios</h1>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="admin-filter-bar">
        <label htmlFor="status-filter">Filtrar por status:</label>
        <select
          id="status-filter"
          value={statusFilter}
          onChange={handleStatusChange}
          className="admin-select"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {loading && (
        <div aria-busy="true">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonListRow key={i} />
          ))}
        </div>
      )}

      {!loading && bets.length === 0 && (
        <p className="empty-state">Nenhum desafio encontrado</p>
      )}

      {!loading && bets.length > 0 && (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Título</th>
                <th>Categoria</th>
                <th>Status</th>
                <th>Participantes</th>
                <th>Pote</th>
                <th>Criada em</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {bets.map((bet) => (
                <tr key={bet.id}>
                  <td>{bet.title}</td>
                  <td>{bet.category}</td>
                  <td>
                    <span
                      className={`status-badge status-${bet.status}`}
                    >
                      {STATUS_LABELS[bet.status] || bet.status}
                    </span>
                  </td>
                  <td>{bet.current_participants}</td>
                  <td>{formatCurrency(bet.pot_total)}</td>
                  <td>{formatDate(bet.created_at)}</td>
                  <td className="admin-actions-cell">
                    {canAct(bet.status) && (
                      <>
                        <button
                          className="btn-action btn-action-primary"
                          onClick={() => openResolveModal(bet)}
                        >
                          Resolver
                        </button>
                        {confirmCancelId === bet.id ? (
                          <span className="admin-confirm-group">
                            <span className="admin-confirm-text">
                              Cancelar?
                            </span>
                            <button
                              className="btn-action btn-action-danger"
                              onClick={() => handleForceCancel(bet.id)}
                            >
                              Sim
                            </button>
                            <button
                              className="btn-action btn-action-secondary"
                              onClick={() => setConfirmCancelId(null)}
                            >
                              Não
                            </button>
                          </span>
                        ) : (
                          <button
                            className="btn-action btn-action-danger"
                            onClick={() => setConfirmCancelId(bet.id)}
                          >
                            Cancelar
                          </button>
                        )}
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="admin-pagination">
        <button
          className="btn btn-secondary btn-sm"
          disabled={page <= 1}
          onClick={() => setPage(page - 1)}
        >
          Anterior
        </button>
        <span className="admin-page-indicator">Página {page}</span>
        <button
          className="btn btn-secondary btn-sm"
          disabled={bets.length < 20}
          onClick={() => setPage(page + 1)}
        >
          Próxima
        </button>
      </div>

      {resolveModal && (
        <div className="admin-modal-overlay" onClick={() => setResolveModal(null)}>
          <div
            className="admin-modal-card card"
            onClick={(e) => e.stopPropagation()}
          >
            <h2>Resolver Desafio</h2>
            <p className="admin-modal-subtitle">{resolveModal.title}</p>

            <div className="form-group">
              <label>Selecione a opção vencedora:</label>
              {resolveModal.options.map((opt) => (
                <label key={opt.id} className="admin-radio-label">
                  <input
                    type="radio"
                    name="winning_option"
                    value={opt.id}
                    checked={selectedOptionId === opt.id}
                    onChange={() => setSelectedOptionId(opt.id)}
                  />
                  {opt.label}
                </label>
              ))}
            </div>

            <div className="admin-modal-actions">
              <button
                className="btn btn-primary"
                onClick={handleForceResolve}
                disabled={!selectedOptionId}
              >
                Confirmar Resolução
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setResolveModal(null)}
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
