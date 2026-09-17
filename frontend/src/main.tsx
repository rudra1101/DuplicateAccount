import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { installAuthenticatedFetch } from "./auth/installAuthenticatedFetch";
import BrandingThemeProvider from "./theme/BrandingThemeProvider";

installAuthenticatedFetch();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrandingThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </BrandingThemeProvider>
  </React.StrictMode>
);