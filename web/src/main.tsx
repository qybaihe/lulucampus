import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AppProvider } from "./app/AppContext";
import App from "./App";
import "./styles/tokens.css";
import "./styles/app.css";
import "./styles/shell-overrides.css";
import "./styles/landing.css";
import "./styles/taste.css";

// Vite BASE_URL is "/" in dev and e.g. "/onemore/" when built with --base.
const routerBasename = import.meta.env.BASE_URL.replace(/\/$/, "") || "/";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={routerBasename}>
      <AppProvider>
        <App />
      </AppProvider>
    </BrowserRouter>
  </StrictMode>,
);
