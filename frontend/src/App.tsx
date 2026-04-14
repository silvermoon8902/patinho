import { Routes, Route } from "react-router-dom";
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

function NotFound() {
  return (
    <div className="not-found">
      <h1>404</h1>
      <p>Pagina nao encontrada</p>
      <a href="/" className="btn btn-primary">
        Voltar ao inicio
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
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </ErrorBoundary>
  );
}
