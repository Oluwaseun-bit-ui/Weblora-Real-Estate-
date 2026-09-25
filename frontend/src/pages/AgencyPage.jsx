import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { AgencyStatusBadge } from "../components/VerificationBadge.jsx";
import PropertyCard from "../components/PropertyCard.jsx";

export default function AgencyPage() {
  const { slug } = useParams();
  const [agency, setAgency] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getAgency(slug)
      .then(setAgency)
      .catch(() => setError("Could not load this agency."));
  }, [slug]);

  if (error) return <p className="status-message status-message--error">{error}</p>;
  if (!agency) return <p className="status-message">Loading…</p>;

  return (
    <div className="agency-page">
      <header className="agency-page__header">
        {agency.logo_url && <img src={agency.logo_url} alt={agency.name} className="agency-page__logo" />}
        <div>
          <h1>{agency.name}</h1>
          <AgencyStatusBadge status={agency.verification_status} badges={agency.verification_badges} />
        </div>
      </header>

      <p className="agency-page__description">{agency.description}</p>

      <div className="agency-page__contact">
        {agency.website && <a href={agency.website} target="_blank" rel="noreferrer">{agency.website}</a>}
        {agency.phone_number && <span>{agency.phone_number}</span>}
        {agency.email && <span>{agency.email}</span>}
      </div>

      {agency.service_locations && agency.service_locations.length > 0 && (
        <p className="agency-page__service-locations">Serves: {agency.service_locations.join(", ")}</p>
      )}

      <h2>Active listings</h2>
      <div className="property-grid">
        {(agency.active_properties || []).map((property) => (
          <PropertyCard key={property.id} property={property} />
        ))}
        {(!agency.active_properties || agency.active_properties.length === 0) && (
          <p className="status-message">No active listings from this agency right now.</p>
        )}
      </div>
    </div>
  );
}
