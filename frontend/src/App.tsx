import { Navigate, Outlet, Routes, Route } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

import AuthLayout from './layouts/AuthLayout';
import AppLayout from './layouts/AppLayout';

import LoginPage from './pages/auth/LoginPage';
import SignupPage from './pages/auth/SignupPage';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';

import DashboardPage from './pages/app/DashboardPage';
import DatasetsPage from './pages/app/DatasetsPage';
import DatasetDetailPage from './pages/app/DatasetDetailPage';
import DatasetUploadPage from './pages/app/DatasetUploadPage';
import ProfilePage from './pages/app/ProfilePage';
import AnalysisPage from './pages/app/AnalysisPage';
import VisualizationsPage from './pages/app/VisualizationsPage';
import InsightsPage from './pages/app/InsightsPage';
import ReportsPage from './pages/app/ReportsPage';
import CreateReportPage from './pages/app/CreateReportPage';
import ReportDetailPage from './pages/app/ReportDetailPage';
import ReportBuilderPage from './pages/app/ReportBuilderPage';
import SettingsPage from './pages/app/SettingsPage';

import LandingPage from './pages/LandingPage';
import NotFoundPage from './pages/NotFoundPage';

// ---------------------------------------------------------------------------
// RequireAuth — route guard for authenticated pages.
//
// BACKEND INTEGRATION POINT:
// Currently checks the in-memory AuthContext flag set by devSignIn().
// When real session/token authentication is implemented, replace the
// `isAuthenticated` check with a proper token validation call from
// authService or the auth context.
// ---------------------------------------------------------------------------

function RequireAuth() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    // Redirect to login, preserving the intended URL for post-login redirect.
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

function App() {
  return (
    <Routes>
      {/* Landing page — no layout wrapper; fully self-contained */}
      <Route path="/" element={<LandingPage />} />

      {/* Public Routes (Auth) */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      </Route>

      {/* Protected Routes (App) — guarded by RequireAuth */}
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />

          {/* Dataset Management */}
          <Route path="/datasets" element={<DatasetsPage />} />
          {/*
            Phase 2F: Upload must come before /:datasetId so the literal
            string "upload" is not treated as a dataset ID.
          */}
          <Route path="/datasets/upload" element={<DatasetUploadPage />} />
          <Route path="/datasets/:datasetId" element={<DatasetDetailPage />} />

          {/* Analytics */}
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/visualizations" element={<VisualizationsPage />} />
          <Route path="/insights" element={<InsightsPage />} />
          <Route path="/insights/what-if" element={<InsightsPage subView="what-if" />} />

          {/* Output */}
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/reports/create" element={<CreateReportPage />} />
          <Route path="/reports/:reportId" element={<ReportDetailPage />} />
          <Route path="/reports/:reportId/edit" element={<ReportBuilderPage />} />

          {/* Account */}
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      {/* Fallback for unknown routes */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default App;
