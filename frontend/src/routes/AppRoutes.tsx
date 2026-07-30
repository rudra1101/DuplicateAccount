import { Routes, Route } from "react-router-dom";

import MainLayout from "../layouts/MainLayout/Mainlayout";
import Dashboard from "../pages/Dashboard/Dashboard";
import DuplicateDetection from "../pages/DuplicateDetection/DuplicateDetection";
import Reports from "../pages/Reports/Reports";
import Admin from "../pages/Admin/Admin";
import Settings from "../pages/Settings/Settings";
import ReviewQueue from "../pages/Review/ReviewQueue";
import ApplicationDetails from "../pages/Review/ApplicationDetails";
import UploadAccounts from "../pages/upload/UploadAccounts";

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
        <Route path="review/:application" element={<ApplicationDetails />} />
        <Route path="upload" element={<UploadAccounts />} />
      </Route>
    </Routes>
  );
};

export default AppRoutes;