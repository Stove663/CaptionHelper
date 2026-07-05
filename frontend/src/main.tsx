import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App";
import EditorPage from "./pages/EditorPage";
import HomePage from "./pages/HomePage";
import PreviewPage from "./pages/PreviewPage";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<HomePage />} />
          <Route path="projects/:id/edit" element={<EditorPage />} />
          <Route path="projects/:id/preview" element={<PreviewPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
