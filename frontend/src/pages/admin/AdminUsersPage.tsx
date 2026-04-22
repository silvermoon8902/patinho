import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import type { RootState, AppDispatch } from "@/store";
import {
  fetchAdminUsers,
  toggleUserActive,
  makeAdmin,
} from "@/store/adminSlice";
import { SkeletonListRow } from "@/components/shared/Skeleton";

export default function AdminUsersPage() {
  const dispatch = useDispatch<AppDispatch>();
  const { users, loading, error } = useSelector(
    (state: RootState) => state.admin
  );
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [confirmAdminId, setConfirmAdminId] = useState<string | null>(null);

  useEffect(() => {
    dispatch(fetchAdminUsers({ search: search || undefined, page }));
  }, [dispatch, page]);

  function handleSearch() {
    setPage(1);
    dispatch(fetchAdminUsers({ search: search || undefined, page: 1 }));
  }

  function handleSearchKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleSearch();
  }

  function handleToggleActive(userId: string, currentActive: boolean) {
    dispatch(toggleUserActive({ userId, isActive: !currentActive }));
  }

  function handleMakeAdmin(userId: string) {
    dispatch(makeAdmin(userId));
    setConfirmAdminId(null);
  }

  return (
    <div className="admin-page">
      <h1 className="admin-page-title">Gerenciar Usuários</h1>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="admin-search-bar">
        <input
          type="text"
          placeholder="Buscar por email ou username..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={handleSearchKeyDown}
        />
        <button className="btn btn-primary btn-sm" onClick={handleSearch}>
          Buscar
        </button>
      </div>

      {loading && (
        <div aria-busy="true">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonListRow key={i} />
          ))}
        </div>
      )}

      {!loading && users.length === 0 && (
        <p className="empty-state">Nenhum usuário encontrado</p>
      )}

      {!loading && users.length > 0 && (
        <div className="admin-users-list">
          {users.map((user) => (
            <div key={user.id} className="admin-user-card">
              <div className="admin-user-head">
                <div className="admin-user-identity">
                  <span className="admin-user-name">{user.username}</span>
                  {user.is_admin && (
                    <span className="admin-badge">Admin</span>
                  )}
                </div>
                <span
                  className={
                    user.is_active
                      ? "status-badge status-active"
                      : "status-badge status-inactive"
                  }
                >
                  {user.is_active ? "Ativo" : "Inativo"}
                </span>
              </div>

              <div className="admin-user-info">
                <div className="admin-user-row">
                  <span className="admin-user-label">E-mail</span>
                  <span className="admin-user-value">{user.email}</span>
                </div>
                <div className="admin-user-row">
                  <span className="admin-user-label">Telefone</span>
                  <span className="admin-user-value">{user.phone || "-"}</span>
                </div>
                <div className="admin-user-row">
                  <span className="admin-user-label">Pontos</span>
                  <span className="admin-user-value">{user.total_points}</span>
                </div>
              </div>

              <div className="admin-user-actions">
                <button
                  className={
                    user.is_active
                      ? "btn-action btn-action-danger"
                      : "btn-action btn-action-success"
                  }
                  onClick={() => handleToggleActive(user.id, user.is_active)}
                >
                  {user.is_active ? "Desativar" : "Ativar"}
                </button>
                {!user.is_admin && (
                  <>
                    {confirmAdminId === user.id ? (
                      <span className="admin-confirm-group">
                        <span className="admin-confirm-text">Confirmar?</span>
                        <button
                          className="btn-action btn-action-success"
                          onClick={() => handleMakeAdmin(user.id)}
                        >
                          Sim
                        </button>
                        <button
                          className="btn-action btn-action-secondary"
                          onClick={() => setConfirmAdminId(null)}
                        >
                          Não
                        </button>
                      </span>
                    ) : (
                      <button
                        className="btn-action btn-action-primary"
                        onClick={() => setConfirmAdminId(user.id)}
                      >
                        Tornar Admin
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
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
          disabled={users.length < 20}
          onClick={() => setPage(page + 1)}
        >
          Próxima
        </button>
      </div>
    </div>
  );
}
