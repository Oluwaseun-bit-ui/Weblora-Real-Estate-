import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client.js";
import SearchFilters from "../components/SearchFilters.jsx";
import PropertyCard from "../components/PropertyCard.jsx";
import WebResultCard from "../components/WebResultCard.jsx";

export default function SearchPage() {
  const [filters, setFilters] = useState({});
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [web, setWeb] = useState(null); // null = not searched yet
  const [webLoading, setWebLoading] = useState(false);

  const runSearch = useCallback(async (activeFilters) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchProperties(activeFilters);
      setResults(data.results || []);
    } catch (err) {
      setError("Something went wrong loading properties. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Web results cost a paid API call and take a few seconds, so they only
  // run when the customer actually presses Search (not on page load).
  const runWebSearch = useCallback(async (activeFilters) => {
    setWebLoading(true);
    try {
      setWeb(await api.searchWeb(activeFilters));
    } catch (err) {
      setWeb({ available: false, reason: "upstream_error", results: [] });
    } finally {
      setWebLoading(false);
    }
  }, []);

  useEffect(() => {
    runSearch(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSubmit = () => {
    runSearch(filters);
    runWebSearch(filters);
  };

  return (
    <div className="search-page">
      <section className="search-hero">
        <h1>Find your next home in Lagos — from verified agencies</h1>
        <p>Search once instead of dozens of sites, Instagram pages and Facebook listings.</p>
      </section>

      <SearchFilters filters={filters} onChange={setFilters} onSubmit={onSubmit} />

      {loading && <p className="status-message">Searching…</p>}
      {error && <p className="status-message status-message--error">{error}</p>}
      {!loading && !error && results.length === 0 && (
        <p className="status-message">No properties matched your search yet. Try widening your filters.</p>
      )}

      <div className="property-grid">
        {results.map((property) => (
          <PropertyCard key={property.id} property={property} />
        ))}
      </div>

      {(webLoading || web?.available) && (
        <section className="web-results">
          <h2>More results from the web</h2>
          <p className="web-results__warning">
            ⚠ These agents were found on other websites and have <strong>not been checked by Weblora</strong>. Never pay
            money before inspecting a property and confirming the agent is genuine.
          </p>
          {webLoading && <p className="status-message">Searching other websites…</p>}
          {!webLoading && web.results.length === 0 && <p className="status-message">Nothing extra found on the web.</p>}
          {!webLoading && web.results.map((r) => <WebResultCard key={r.url} result={r} />)}
        </section>
      )}
    </div>
  );
}
