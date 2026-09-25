import { Routes, Route, Link } from "react-router-dom";
import SearchPage from "./pages/SearchPage.jsx";
import PropertyDetailPage from "./pages/PropertyDetailPage.jsx";
import AgencyPage from "./pages/AgencyPage.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <header className="site-header">
        <Link to="/" className="logo">
          🏠 PropertyFinder NG
        </Link>
        <span className="tagline">Search once. Find verified agencies.</span>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/properties/:id" element={<PropertyDetailPage />} />
          <Route path="/agencies/:slug" element={<AgencyPage />} />
        </Routes>
      </main>
      <footer className="site-footer">
        <p>
          Properties are discovered from permitted sources and agency-provided data. Verification
          badges show exactly what was checked — we never claim a property or agency is
          "100% trusted".
        </p>
      </footer>
    </div>
  );
}
