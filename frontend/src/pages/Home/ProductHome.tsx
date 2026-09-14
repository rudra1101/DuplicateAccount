import type { ReactNode } from "react";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import GridViewOutlinedIcon from "@mui/icons-material/GridViewOutlined";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";
import UpcomingOutlinedIcon from "@mui/icons-material/UpcomingOutlined";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
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

import Header from "../../components/layouts/Header";

type DomainStatus = "AVAILABLE" | "COMING_SOON";

interface ProductDomain {
  id: string;
  name: string;
  description: string;
  route: string;
  status: DomainStatus;
  icon: ReactNode;
}

const domains: ProductDomain[] = [
  {
    id: "account-intelligence",
    name: "Account Duplicate & Orphan Detection",
    description:
      "Discover duplicate accounts, identify orphan accounts, review findings, and manage source integrations.",
    route: "/dashboard",
    status: "AVAILABLE",
    icon: <AccountTreeOutlinedIcon sx={{ fontSize: 34 }} />,
  },
  {
    id: "account-heatmap",
    name: "Account Heatmap",
    description:
      "Visualize account distribution, concentration, activity, and identity patterns across connected sources.",
    route: "/account-heatmap",
    status: "AVAILABLE",
    icon: <GridViewOutlinedIcon sx={{ fontSize: 34 }} />,
  },
  {
    id: "non-human-identity",
    name: "Non-Human Identity",
    description:
      "Discover and govern service accounts, shared accounts, bots, workloads, and other non-human identities.",
    route: "/non-human-identities",
    status: "AVAILABLE",
    icon: <SmartToyOutlinedIcon sx={{ fontSize: 34 }} />,
  },
  {
    id: "domain-4",
    name: "Domain 4",
    description:
      "Reserved for the next IdentityAI capability based on the client's future requirements.",
    route: "",
    status: "COMING_SOON",
    icon: <UpcomingOutlinedIcon sx={{ fontSize: 34 }} />,
  },
];

const ProductHome = () => {
  const navigate = useNavigate();

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#f5f7fa" }}>
      <Header />
      <Container maxWidth="lg" sx={{ py: { xs: 4, md: 7 } }}>
        <Box sx={{ mb: 4.5 }}>
          <Typography variant="h4" fontWeight={800}>
            IdentityAI
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ mt: 1 }}>
            Choose a domain to continue
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 760 }}>
            IdentityAI is organized into focused identity intelligence domains. Select the workspace you want to use.
          </Typography>
        </Box>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
            gap: 3,
          }}
        >
          {domains.map((domain) => {
            const available = domain.status === "AVAILABLE";
            return (
              <Card
                key={domain.id}
                variant="outlined"
                sx={{
                  minHeight: 245,
                  borderRadius: 3,
                  borderColor: available ? "divider" : "rgba(15,23,42,0.10)",
                  bgcolor: available ? "background.paper" : "rgba(255,255,255,0.65)",
                  transition: "transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease",
                  ...(available && {
                    "&:hover": {
                      transform: "translateY(-3px)",
                      boxShadow: "0 16px 40px rgba(15, 23, 42, 0.10)",
                      borderColor: "primary.light",
                    },
                  }),
                }}
              >
                <CardActionArea
                  disabled={!available}
                  onClick={() => available && navigate(domain.route)}
                  sx={{ height: "100%", alignItems: "stretch" }}
                >
                  <CardContent sx={{ p: 3.5, height: "100%" }}>
                    <Stack spacing={2.25} height="100%">
                      <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                        <Box
                          sx={{
                            width: 58,
                            height: 58,
                            borderRadius: 2.5,
                            display: "grid",
                            placeItems: "center",
                            bgcolor: available ? "primary.main" : "action.disabledBackground",
                            color: available ? "primary.contrastText" : "text.disabled",
                          }}
                        >
                          {domain.icon}
                        </Box>
                        <Chip
                          size="small"
                          label={available ? "Available" : "Coming Soon"}
                          color={available ? "success" : "default"}
                          variant={available ? "filled" : "outlined"}
                        />
                      </Stack>

                      <Box sx={{ flex: 1 }}>
                        <Typography variant="h6" fontWeight={800}>
                          {domain.name}
                        </Typography>
                        <Typography color="text.secondary" sx={{ mt: 1.25, lineHeight: 1.65 }}>
                          {domain.description}
                        </Typography>
                      </Box>

                      {available && (
                        <Stack direction="row" spacing={1} alignItems="center" color="primary.main">
                          <Typography variant="body2" fontWeight={800}>
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
      </Container>
    </Box>
  );
};

export default ProductHome;
