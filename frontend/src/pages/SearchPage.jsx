import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client.js";
import SearchFilters from "../components/SearchFilters.jsx";
import PropertyCard from "../components/PropertyCard.jsx";

export default function SearchPage() {
  const [filters, setFilters] = useState({});
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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

  useEffect(() => {
    runSearch(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="search-page">
      <section className="search-hero">
        <h1>Find your next home in Lagos — from verified agencies</h1>
        <p>Search once instead of dozens of sites, Instagram pages and Facebook listings.</p>
      </section>

      <SearchFilters filters={filters} onChange={setFilters} onSubmit={() => runSearch(filters)} />

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
    </div>
  );
}
