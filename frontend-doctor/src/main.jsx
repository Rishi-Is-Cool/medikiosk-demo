import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "../../shared/tokens.css";
import "./styles/app.css";
import "./styles/shell.css";
import "./styles/app-shell.css";
import "./styles/home.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
