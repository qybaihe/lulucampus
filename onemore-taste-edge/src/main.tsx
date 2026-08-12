import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { DemoTasteScreen } from "./DemoTasteScreen";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <DemoTasteScreen />
  </StrictMode>,
);
