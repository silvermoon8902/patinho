import { Routes, Route, Navigate } from "react-router-dom";
import ErrorBoundary from "@/components/shared/ErrorBoundary";
import Layout from "@/components/shared/Layout";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import DashboardPage from "@/pages/dashboard/DashboardPage";
import WalletPage from "@/pages/wallet/WalletPage";
import BetsListPage from "@/pages/bets/BetsListPage";
import CreateBetPage from "@/pages/bets/CreateBetPage";
import BetDetailPage from "@/pages/bets/BetDetailPage";
import InvitePage from "@/pages/invite/InvitePage";
import RankingPage from "@/pages/ranking/RankingPage";
import ProfilePage from "@/pages/profile/ProfilePage";
import AdminDashboardPage from "@/pages/admin/AdminDashboardPage";
import AdminUsersPage from "@/pages/admin/AdminUsersPage";
import AdminBetsPage from "@/pages/admin/AdminBetsPage";
import AdminFeePage from "@/pages/admin/AdminFeePage";
import { useAuth } from "@/hooks/useAuth";

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user?.is_admin) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

function NotFound() {
  return (
    <div className="not-found">
      <h1>404</h1>
      <p>Página não encontrada</p>
      <a href="/" className="btn btn-primary">
        Voltar ao início
      </a>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/invite/:inviteToken" element={<InvitePage />} />
        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/bets" element={<BetsListPage />} />
          <Route path="/bets/create" element={<CreateBetPage />} />
          <Route path="/bets/:betId" element={<BetDetailPage />} />
          <Route path="/wallet" element={<WalletPage />} />
          <Route path="/ranking" element={<RankingPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route
            path="/admin"
            element={
              <AdminRoute>
                <AdminDashboardPage />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <AdminRoute>
                <AdminUsersPage />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/bets"
            element={
              <AdminRoute>
                <AdminBetsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/fee"
            element={
              <AdminRoute>
                <AdminFeePage />
              </AdminRoute>
            }
          />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </ErrorBoundary>
  );
}
