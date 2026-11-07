import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { LangProvider } from "./i18n";
import { JourneyProvider } from "./state/journey";
import { MetaProvider } from "./state/meta";
import "./index.css";

// Follow the device's light/dark setting; the theme's dark tokens hang off a .dark class on <html>.
const darkQuery = window.matchMedia?.("(prefers-color-scheme: dark)");
const applyScheme = () => document.documentElement.classList.toggle("dark", !!darkQuery?.matches);
applyScheme();
darkQuery?.addEventListener?.("change", applyScheme);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <LangProvider>
        <MetaProvider>
          <JourneyProvider>
            <App />
          </JourneyProvider>
        </MetaProvider>
      </LangProvider>
    </BrowserRouter>
  </StrictMode>,
);
