import { Route, Routes } from "react-router-dom";

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
import ApplicationReview from "../pages/review/ApplicationReview";
import UploadAccounts from "../pages/upload/UploadAccounts";
import Integrations from "../pages/integrations/Integrations";
import AddIntegration from "../pages/integrations/AddIntegration";
import Operations from "../pages/operations/Operations";
import MlTrainingDashboard from "../pages/ml/MlTrainingDashboard";
import KnowledgeBase from "../pages/knowledge/KnowledgeBase";

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="duplicates" element={<DuplicateDetection />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
          <Route path="review" element={<ReviewQueue />} />
          <Route path="review/:application" element={<ApplicationReview />} />
          <Route path="upload" element={<UploadAccounts />} />
          <Route path="operations" element={<Operations />} />
          <Route path="ml-training" element={<MlTrainingDashboard />} />

          <Route element={<PermissionRoute anyOf={["integration.view"]} />}>
            <Route path="integrations" element={<Integrations />} />
          </Route>

          <Route element={<PermissionRoute anyOf={["user.view", "role.view"]} />}>
            <Route path="admin" element={<Admin />} />
          </Route>

          <Route element={<PermissionRoute anyOf={["user.view"]} />}>
            <Route path="users" element={<Admin />} />
          </Route>

          <Route element={<PermissionRoute anyOf={["integration.create"]} />}>
            <Route path="integrations/new" element={<AddIntegration />} />
          </Route>

          <Route element={<PermissionRoute anyOf={["integration.edit"]} />}>
            <Route path="integrations/:integrationId/edit" element={<AddIntegration />} />
          </Route>
        </Route>

        <Route path="/knowledge" element={<KnowledgeBase />} />
      </Route>
    </Routes>
  );
};

export default AppRoutes;
