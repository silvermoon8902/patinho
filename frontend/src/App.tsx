import { Routes, Route, Navigate } from "react-router-dom";
import ErrorBoundary from "@/components/shared/ErrorBoundary";
import Layout from "@/components/shared/Layout";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/auth/ResetPasswordPage";
import DashboardPage from "@/pages/dashboard/DashboardPage";
import WalletPage from "@/pages/wallet/WalletPage";
import BetsListPage from "@/pages/bets/BetsListPage";
import CreateBetPage from "@/pages/bets/CreateBetPage";
import BetDetailPage from "@/pages/bets/BetDetailPage";
import LeaguesListPage from "@/pages/leagues/LeaguesListPage";
import LeagueDetailPage from "@/pages/leagues/LeagueDetailPage";
import InvitePage from "@/pages/invite/InvitePage";
import RankingPage from "@/pages/ranking/RankingPage";
import ProfilePage from "@/pages/profile/ProfilePage";
import AdminDashboardPage from "@/pages/admin/AdminDashboardPage";
import AdminUsersPage from "@/pages/admin/AdminUsersPage";
import AdminBetsPage from "@/pages/admin/AdminBetsPage";
import AdminFeePage from "@/pages/admin/AdminFeePage";
import TermsPage from "@/pages/legal/TermsPage";
import PrivacyPage from "@/pages/legal/PrivacyPage";
import LgpdPage from "@/pages/legal/LgpdPage";
import CreateBolaoPage from "@/pages/tournament/CreateBolaoPage";
import TournamentPalpitesPage from "@/pages/tournament/TournamentPalpitesPage";
import TournamentRankingPage from "@/pages/tournament/TournamentRankingPage";
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
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
        <Route path="/invite/:inviteToken" element={<InvitePage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/lgpd" element={<LgpdPage />} />
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
          <Route path="/bolao/create" element={<CreateBolaoPage />} />
          <Route path="/bets/:betId/palpites" element={<TournamentPalpitesPage />} />
          <Route path="/bets/:betId/ranking" element={<TournamentRankingPage />} />
          <Route path="/bets/:betId" element={<BetDetailPage />} />
          <Route path="/leagues" element={<LeaguesListPage />} />
          <Route path="/leagues/join/:joinCode" element={<LeaguesListPage />} />
          <Route path="/leagues/:leagueId" element={<LeagueDetailPage />} />
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
