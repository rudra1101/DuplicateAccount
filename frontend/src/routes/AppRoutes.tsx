import { Navigate, Route, Routes } from "react-router-dom";

import PermissionRoute from "../auth/PermissionRoute";
import ProtectedRoute from "../auth/ProtectedRoute";
import MainLayout from "../layouts/MainLayout/Mainlayout";

import Dashboard from "../pages/Dashboard/Dashboard";
import DuplicateDetection from "../pages/DuplicateDetection/DuplicateDetection";
import Reports from "../pages/Reports/Reports";
import Admin from "../pages/Admin/Admin";
import Settings from "../pages/Settings/Settings";
import LoginPage from "../pages/Login/LoginPage";
import ReviewQueue from "../pages/Review/ReviewQueue";
import ApplicationReview from "../pages/Review/ApplicationReview";
import RemediationQueue from "../pages/remediation/RemediationQueue";
import UploadAccounts from "../pages/upload/UploadAccounts";
import Integrations from "../pages/integrations/Integrations";
import SourceWizard from "../pages/integrations/SourceWizard";
import AccountInventory from "../pages/accounts/AccountInventory";
import OperationsWorkspace from "../pages/operations/OperationsWorkspace";
import MlTrainingDashboard from "../pages/ml/MlTrainingDashboard";
import ReviewerAnalytics from "../pages/ml/ReviewerAnalytics";
import KnowledgeBase from "../pages/knowledge/KnowledgeBase";
import ProductHome from "../pages/Home/ProductHome";
import DomainPlaceholder from "../pages/Home/DomainPlaceholder";

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/home" element={<ProductHome />} />

        <Route element={<PermissionRoute anyOf={["domain.account_heatmap.view"]} />}>
          <Route
            path="/account-heatmap"
            element={
              <DomainPlaceholder
                title="Account Heatmap"
                description="Account distribution, concentration, activity, and identity-pattern analytics will live in this domain."
              />
            }
          />
        </Route>

        <Route element={<PermissionRoute anyOf={["domain.non_human_identity.view"]} />}>
          <Route
            path="/non-human-identities"
            element={
              <DomainPlaceholder
                title="Non-Human Identity"
                description="Discovery and governance for service accounts, shared accounts, bots, workloads, and other non-human identities will live in this domain."
              />
            }
          />
        </Route>

        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/home" replace />} />

          {/* Account Intelligence domain */}
          <Route element={<PermissionRoute anyOf={["domain.account_intelligence.view"]} />}>
            <Route element={<PermissionRoute anyOf={["dashboard.view"]} />}>
              <Route path="account-intelligence/dashboard" element={<Dashboard />} />
            </Route>

            <Route element={<PermissionRoute anyOf={["duplicate.view"]} />}>
              <Route path="account-intelligence/duplicates" element={<DuplicateDetection />} />
            </Route>

            <Route element={<PermissionRoute anyOf={["duplicate.review"]} />}>
              <Route path="account-intelligence/review" element={<ReviewQueue />} />
              <Route path="account-intelligence/review/:application" element={<ApplicationReview />} />
            </Route>

            <Route element={<PermissionRoute anyOf={["report.view"]} />}>
              <Route path="account-intelligence/reports" element={<Reports />} />
            </Route>

            <Route element={<PermissionRoute anyOf={["remediation.view", "remediation.history.view"]} />}>
              <Route path="account-intelligence/remediation" element={<RemediationQueue />} />
            </Route>

            <Route element={<PermissionRoute anyOf={["upload.manage"]} />}>
              <Route path="account-intelligence/upload" element={<UploadAccounts />} />
            </Route>

            <Route element={<PermissionRoute anyOf={["integration.view"]} />}>
              <Route path="account-intelligence/integrations" element={<Integrations />} />
              <Route path="account-intelligence/accounts" element={<AccountInventory />} />
            </Route>

            <Route element={<PermissionRoute anyOf={["integration.create"]} />}>
              <Route path="account-intelligence/integrations/new" element={<SourceWizard />} />
            </Route>

            <Route element={<PermissionRoute anyOf={["integration.edit"]} />}>
              <Route path="account-intelligence/integrations/:integrationId/edit" element={<SourceWizard />} />
            </Route>
          </Route>

          {/* Platform-wide administration and advanced capabilities */}
          <Route element={<PermissionRoute anyOf={["settings.manage"]} />}>
            <Route path="settings" element={<Settings />} />
          </Route>

          <Route element={<PermissionRoute anyOf={["operations.view"]} />}>
            <Route path="operations" element={<OperationsWorkspace />} />
          </Route>

          <Route element={<PermissionRoute anyOf={["ml.view"]} />}>
            <Route path="ml-training" element={<MlTrainingDashboard />} />
          </Route>

          <Route element={<PermissionRoute anyOf={["ml.analytics.view", "ml.calibration.view"]} />}>
            <Route path="ml-evaluation" element={<ReviewerAnalytics />} />
          </Route>

          <Route element={<PermissionRoute anyOf={["user.view", "role.view"]} />}>
            <Route path="admin" element={<Admin />} />
          </Route>

          <Route element={<PermissionRoute anyOf={["user.view"]} />}>
            <Route path="users" element={<Admin />} />
          </Route>

          <Route element={<PermissionRoute anyOf={["knowledge.view"]} />}>
            <Route path="knowledge" element={<KnowledgeBase />} />
          </Route>

          {/* Backward-compatible aliases for pre-domain URLs. */}
          <Route path="dashboard" element={<Navigate to="/account-intelligence/dashboard" replace />} />
          <Route path="duplicates" element={<Navigate to="/account-intelligence/duplicates" replace />} />
          <Route path="review" element={<Navigate to="/account-intelligence/review" replace />} />
          <Route path="reports" element={<Navigate to="/account-intelligence/reports" replace />} />
          <Route path="remediation" element={<Navigate to="/account-intelligence/remediation" replace />} />
          <Route path="upload" element={<Navigate to="/account-intelligence/upload" replace />} />
          <Route path="integrations" element={<Navigate to="/account-intelligence/integrations" replace />} />
          <Route path="accounts" element={<Navigate to="/account-intelligence/accounts" replace />} />

          {/* Parameterized legacy aliases remain functional while old deep links are retired. */}
          <Route element={<PermissionRoute anyOf={["domain.account_intelligence.view"]} />}>
            <Route element={<PermissionRoute anyOf={["duplicate.review"]} />}>
              <Route path="review/:application" element={<ApplicationReview />} />
            </Route>
            <Route element={<PermissionRoute anyOf={["integration.create"]} />}>
              <Route path="integrations/new" element={<SourceWizard />} />
            </Route>
            <Route element={<PermissionRoute anyOf={["integration.edit"]} />}>
              <Route path="integrations/:integrationId/edit" element={<SourceWizard />} />
            </Route>
          </Route>
        </Route>
      </Route>
    </Routes>
  );
};

export default AppRoutes;
