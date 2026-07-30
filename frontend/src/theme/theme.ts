import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    primary: {
      main: "#1565C0",
    },
    secondary: {
      main: "#1976D2",
    },
    background: {
      default: "#F5F7FA",
    },
  },

  shape: {
    borderRadius: 10,
  },

  typography: {
    fontFamily: "Roboto, sans-serif",
  },
});

export default theme;