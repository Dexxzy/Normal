import React from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "react-hot-toast";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
    <Toaster
      position="bottom-right"
      toastOptions={{
        style: {
          background: "#1a1917",
          color: "#b0ada7",
          border: "1px solid #242220",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "12px",
          borderRadius: "8px",
        },
        success: { iconTheme: { primary: "#f59e0b", secondary: "#0c0c0d" } },
        error:   { iconTheme: { primary: "#f87171", secondary: "#0c0c0d" } },
      }}
    />
  </React.StrictMode>
);
