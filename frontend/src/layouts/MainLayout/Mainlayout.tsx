import { Outlet } from "react-router-dom";
import { Box } from "@mui/material";
import Sidebar from "../../components/layouts/Sidebar";
import Header from "../../components/layouts/Header";
import FloatingChat from "../../components/chatbot/FloatingChat";

const MainLayout = () => {
  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "#f5f7fa" }}>
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Top Header */}
        <Header />

        {/* Page Content */}
        <Box
          sx={{
            flexGrow: 1,
            p: 3,
            overflow: "auto",
          }}
        >
          <Outlet />
        </Box>

        {/* Floating AI Chatbot */}
        <FloatingChat />
      </Box>
    </Box>
  );
};

export default MainLayout;