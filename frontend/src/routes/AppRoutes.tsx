import { Route, Routes } from "react-router-dom";

import ProtectedRoute from "../auth/ProtectedRoute";
import RoleRoute from "../auth/RoleRoute";
import MainLayout from "../layouts/MainLayout/Mainlayout";

import Dashboard from "../pages/Dashboard/Dashboard";
import DuplicateDetection from "../pages/DuplicateDetection/DuplicateDetection";
import Reports from "../pages/Reports/Reports";
import Admin from "../pages/Admin/Admin";
import UserManagement from "../pages/Admin/UserManagement";
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
          <Route path="integrations" element={<Integrations />} />
          <Route path="operations" element={<Operations />} />
          <Route path="ml-training" element={<MlTrainingDashboard />} />

          <Route element={<RoleRoute roles={["ADMIN"]} />}>
            <Route path="admin" element={<Admin />} />
            <Route path="users" element={<UserManagement />} />
            <Route path="integrations/new" element={<AddIntegration />} />
            <Route
              path="integrations/:integrationId/edit"
              element={<AddIntegration />}
            />
          </Route>
        </Route>

        <Route path="/knowledge" element={<KnowledgeBase />} />
      </Route>
    </Routes>
  );
};

export default AppRoutes;
