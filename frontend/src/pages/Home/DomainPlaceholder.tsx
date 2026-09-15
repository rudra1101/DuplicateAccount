import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Box, Button, Container, Paper, Stack, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";

import Header from "../../components/layouts/Header";

interface Props {
  title: string;
  description: string;
}

const DomainPlaceholder = ({ title, description }: Props) => {
  const navigate = useNavigate();

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#f5f7fa" }}>
      <Header />
      <Container maxWidth="md" sx={{ py: { xs: 4, md: 7 } }}>
        <Paper variant="outlined" sx={{ p: { xs: 3, md: 5 }, borderRadius: 3 }}>
          <Stack spacing={2.5}>
            <Typography variant="h4" fontWeight={800}>{title}</Typography>
            <Typography color="text.secondary" sx={{ fontSize: 17, lineHeight: 1.7 }}>
              {description}
            </Typography>
            <Typography color="text.secondary">
              This workspace entry point is ready. Domain-specific capabilities will be added as requirements are finalized.
            </Typography>
            <Box>
              <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/home")}>
                Back to IdentityAI Home
              </Button>
            </Box>
          </Stack>
        </Paper>
      </Container>
    </Box>
  );
};

export default DomainPlaceholder;
