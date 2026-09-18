import { useMemo, type ReactNode } from "react";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import GridViewOutlinedIcon from "@mui/icons-material/GridViewOutlined";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";
import UpcomingOutlinedIcon from "@mui/icons-material/UpcomingOutlined";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import FingerprintOutlinedIcon from "@mui/icons-material/FingerprintOutlined";
import PersonOutlineOutlinedIcon from "@mui/icons-material/PersonOutlineOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import InsertChartOutlinedIcon from "@mui/icons-material/InsertChartOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import Groups2OutlinedIcon from "@mui/icons-material/Groups2Outlined";
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Container,
  Stack,
  Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";
import Header from "../../components/layouts/Header";

type WorkspaceStatus = "ACTIVE" | "DISABLED" | "COMING_SOON";

interface Workspace {
  id: string;
  name: string;
  description: string;
  route: string;
  status: WorkspaceStatus;
  permission?: string;
  icon: ReactNode;
}

const workspaces: Workspace[] = [
  {
    id: "account-intelligence",
    name: "Duplicate and Orphan Account Detection",
    description:
      "Discover duplicate accounts, identify orphan accounts, review findings, and manage source integrations.",
    route: "/account-intelligence/dashboard",
    status: "ACTIVE",
    permission: "domain.account_intelligence.view",
    icon: <AccountTreeOutlinedIcon sx={{ fontSize: 27 }} />,
  },
  {
    id: "account-heatmap",
    name: "Account Heatmap",
    description:
      "Visualize account distribution, concentration, activity, and identity patterns across connected sources.",
    route: "",
    status: "DISABLED",
    icon: <GridViewOutlinedIcon sx={{ fontSize: 27 }} />,
  },
  {
    id: "non-human-identity",
    name: "Non-Human Identity",
    description:
      "Discover and govern service accounts, shared accounts, bots, workloads, and other non-human identities.",
    route: "",
    status: "DISABLED",
    icon: <SmartToyOutlinedIcon sx={{ fontSize: 27 }} />,
  },
  {
    id: "workspace-4",
    name: "Workspace 4",
    description:
      "Reserved for the next IdentityAI capability based on future requirements.",
    route: "",
    status: "COMING_SOON",
    icon: <UpcomingOutlinedIcon sx={{ fontSize: 27 }} />,
  },
];

const ProductHome = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();

  const visibleWorkspaces = useMemo(
    () =>
      workspaces.filter(
        (workspace) =>
          workspace.status !== "ACTIVE" ||
          !workspace.permission ||
          hasPermission(workspace.permission),
      ),
    [hasPermission],
  );

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at 28% 35%, rgba(21,101,192,0.08), transparent 34%), linear-gradient(135deg, #ffffff 0%, #f7fbff 52%, #f3f8ff 100%)",
        overflow: "hidden",
      }}
    >
      <Header />

      <Container
        maxWidth={false}
        sx={{
          minHeight: "calc(100vh - 64px)",
          px: { xs: 2.5, sm: 4, lg: 6 },
          py: { xs: 4, lg: 5 },
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "minmax(360px, 0.95fr) minmax(620px, 1.45fr)" },
          gap: { xs: 5, lg: 8 },
          alignItems: "center",
        }}
      >
        <Box sx={{ position: "relative", minWidth: 0 }}>
          <Typography
            sx={{
              fontSize: { xs: "3rem", sm: "4rem", lg: "4.4rem" },
              lineHeight: 0.95,
              letterSpacing: "-0.055em",
              fontWeight: 900,
              color: "#07184b",
            }}
          >
            IdentityAI Intelligent Operations
          </Typography>

          <Typography
            sx={{
              mt: 2,
              fontSize: { xs: "1.05rem", sm: "1.25rem" },
              fontWeight: 800,
              color: "primary.main",
            }}
          >
            Intelligent Identity. Confident Decisions.
          </Typography>

          <Typography
            sx={{
              mt: 2,
              maxWidth: 560,
              color: "#627196",
              lineHeight: 1.65,
              fontSize: { xs: "0.95rem", sm: "1.05rem" },
            }}
          >
            An AI-powered identity intelligence platform that helps organizations discover risk,
            strengthen governance, and make faster, evidence-driven access decisions.
          </Typography>

          <Stack spacing={2.2} sx={{ mt: 4.5 }}>
            {[
              { icon: <PersonOutlineOutlinedIcon />, text: "Unified identity insights" },
              { icon: <ShieldOutlinedIcon />, text: "Faster risk detection" },
              { icon: <InsertChartOutlinedIcon />, text: "Actionable governance" },
            ].map((item) => (
              <Stack key={item.text} direction="row" spacing={2} alignItems="center">
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: "50%",
                    bgcolor: "rgba(21,101,192,0.09)",
                    color: "primary.main",
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                  }}
                >
                  {item.icon}
                </Box>
                <Typography sx={{ fontWeight: 800, color: "#11255d", fontSize: "1rem" }}>
                  {item.text}
                </Typography>
              </Stack>
            ))}
          </Stack>

          <Box
            aria-hidden="true"
            sx={{
              display: { xs: "none", md: "block" },
              position: "absolute",
              top: 0,
              right: -20,
              width: 300,
              height: 470,
              opacity: 0.34,
              pointerEvents: "none",
            }}
          >
            <Box sx={{ position: "absolute", inset: "80px 15px 20px 35px", border: "1px solid #90caf9", borderRadius: "50%" }} />
            <Box sx={{ position: "absolute", inset: "155px 85px 95px 105px", border: "1px solid #90caf9", borderRadius: "50%" }} />
            <Box sx={{ position: "absolute", top: 45, right: 85 }}><FingerprintOutlinedIcon sx={{ fontSize: 45, color: "primary.main" }} /></Box>
            <Box sx={{ position: "absolute", top: 135, right: 0 }}><Groups2OutlinedIcon sx={{ fontSize: 40, color: "primary.main" }} /></Box>
            <Box sx={{ position: "absolute", top: 260, right: 70 }}><DescriptionOutlinedIcon sx={{ fontSize: 40, color: "primary.main" }} /></Box>
            <Box sx={{ position: "absolute", top: 345, right: 10 }}><ShieldOutlinedIcon sx={{ fontSize: 40, color: "primary.main" }} /></Box>
          </Box>
        </Box>

        <Box sx={{ minWidth: 0 }}>
          <Typography
            sx={{
              fontSize: { xs: "1.7rem", sm: "2rem" },
              fontWeight: 900,
              color: "#07184b",
              letterSpacing: "-0.025em",
            }}
          >
            Choose a workspace to continue
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.7, mb: 3 }}>
            Select the IdentityAI capability you want to work with.
          </Typography>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
              gap: 2,
            }}
          >
            {visibleWorkspaces.map((workspace) => {
              const active = workspace.status === "ACTIVE";
              const comingSoon = workspace.status === "COMING_SOON";

              return (
                <Card
                  key={workspace.id}
                  variant="outlined"
                  sx={{
                    minHeight: 225,
                    borderRadius: 3,
                    borderColor: active ? "rgba(21,101,192,0.18)" : "rgba(100,116,139,0.18)",
                    bgcolor: active ? "rgba(255,255,255,0.96)" : "rgba(248,250,252,0.72)",
                    boxShadow: active ? "0 10px 34px rgba(15, 42, 89, 0.06)" : "none",
                    opacity: active ? 1 : 0.62,
                    filter: active ? "none" : "grayscale(0.85)",
                    transition: "transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease",
                    ...(active && {
                      "&:hover": {
                        transform: "translateY(-3px)",
                        boxShadow: "0 16px 40px rgba(15,42,89,0.10)",
                        borderColor: "primary.light",
                      },
                    }),
                  }}
                >
                  <CardActionArea
                    disabled={!active}
                    onClick={() => active && navigate(workspace.route)}
                    sx={{ height: "100%", alignItems: "stretch" }}
                  >
                    <CardContent sx={{ p: 2.8, height: "100%" }}>
                      <Stack spacing={1.8} height="100%">
                        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                          <Box
                            sx={{
                              width: 48,
                              height: 48,
                              borderRadius: "50%",
                              display: "grid",
                              placeItems: "center",
                              bgcolor: active ? "primary.main" : "#cbd5e1",
                              color: active ? "primary.contrastText" : "#64748b",
                            }}
                          >
                            {workspace.icon}
                          </Box>

                          {comingSoon && (
                            <Chip
                              size="small"
                              label="Coming Soon"
                              variant="outlined"
                              sx={{ bgcolor: "rgba(255,255,255,0.55)" }}
                            />
                          )}
                        </Stack>

                        <Box sx={{ flex: 1 }}>
                          <Typography
                            sx={{
                              fontSize: "1.02rem",
                              fontWeight: 900,
                              color: active ? "#0b1b50" : "#52617f",
                            }}
                          >
                            {workspace.name}
                          </Typography>
                          <Typography
                            color="text.secondary"
                            sx={{ mt: 1, lineHeight: 1.55, fontSize: "0.88rem" }}
                          >
                            {workspace.description}
                          </Typography>
                        </Box>

                        {active && (
                          <Stack direction="row" spacing={0.8} alignItems="center" color="primary.main">
                            <Typography variant="body2" fontWeight={900}>
                              Open workspace
                            </Typography>
                            <ArrowForwardIcon fontSize="small" />
                          </Stack>
                        )}
                      </Stack>
                    </CardContent>
                  </CardActionArea>
                </Card>
              );
            })}
          </Box>
        </Box>
      </Container>
    </Box>
  );
};

export default ProductHome;
