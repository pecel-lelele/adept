import { createRoot } from "react-dom/client";

import App from "./App";

import "./app/globals.css";
import "./app/workspace.css";
import "./app/insight.css";
import "./app/adept.css";
import "./app/adi.css";

createRoot(document.getElementById("root")!, {
  // Keeps caught errors off reportError(), which would raise the dev overlay.
  onCaughtError: (error, errorInfo) => {
    console.error(error, errorInfo.componentStack);
  },
}).render(<App />);
