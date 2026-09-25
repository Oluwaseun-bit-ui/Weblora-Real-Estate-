import { Link } from "react-router-dom";
import { AgencyStatusBadge } from "./VerificationBadge.jsx";

function formatPrice(price, currency, period) {
  const amount = new Intl.NumberFormat("en-NG").format(price);
  return `${currency === "NGN" ? "₦" : currency}${amount}${period ? `/${period}` : ""}`;
}

export default function PropertyCard({ property }) {
  return (
    <Link to={`/properties/${property.id}`} className="property-card">
      <div className="property-card__image">
        {property.primary_image ? (
          <img src={property.primary_image.image_url} alt={property.title} />
        ) : (
          <div className="property-card__image-placeholder">No photo available</div>
        )}
        {property.is_featured && <span className="badge badge--sponsored">Featured</span>}
        {property.is_stale && <span className="badge badge--stale">May be stale</span>}
      </div>
      <div className="property-card__body">
        <h3>{property.title}</h3>
        <p className="property-card__location">{property.location}</p>
        <p className="property-card__price">{formatPrice(property.price, property.currency, property.price_period)}</p>
        <p className="property-card__meta">
          {property.bedrooms ?? "–"} bed · {property.bathrooms ?? "–"} bath · {property.furnished_status}
        </p>
        {property.agency && (
          <AgencyStatusBadge status={property.agency.verification_status} badges={property.agency.verification_badges} />
        )}
        {property.live_viewing_available && <span className="badge badge--live">🎥 Live viewing available</span>}
      </div>
    </Link>
  );
}
