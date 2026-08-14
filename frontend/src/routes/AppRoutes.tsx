import { Route, Routes } from "react-router-dom";

import MainLayout from "../layouts/MainLayout/Mainlayout";

import Dashboard from "../pages/Dashboard/Dashboard";
import DuplicateDetection from "../pages/DuplicateDetection/DuplicateDetection";
import Reports from "../pages/Reports/Reports";
import Admin from "../pages/Admin/Admin";
import Settings from "../pages/Settings/Settings";

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
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Dashboard />} />

        <Route path="duplicates" element={<DuplicateDetection />} />

        <Route path="reports" element={<Reports />} />

        <Route path="admin" element={<Admin />} />

        <Route path="settings" element={<Settings />} />

        <Route path="review" element={<ReviewQueue />} />

        <Route path="review/:application" element={<ApplicationReview />} />

        <Route path="upload" element={<UploadAccounts />} />

        <Route path="integrations" element={<Integrations />} />

        <Route path="integrations/new" element={<AddIntegration />} />

        <Route
          path="integrations/:integrationId/edit"
          element={<AddIntegration />}
        />

        <Route path="operations" element={<Operations />} />

        <Route path="ml-training" element={<MlTrainingDashboard />} />
      </Route>

      <Route path="/knowledge" element={<KnowledgeBase />} />
    </Routes>
  );
};

export default AppRoutes;
