import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client.js";
import { AgencyStatusBadge, PropertyVerificationLine } from "../components/VerificationBadge.jsx";

function formatPrice(price, currency, period) {
  const amount = new Intl.NumberFormat("en-NG").format(price);
  return `${currency === "NGN" ? "₦" : currency}${amount}${period ? `/${period}` : ""}`;
}

function LiveViewingRequestForm({ property }) {
  const [form, setForm] = useState({ customer_name: "", customer_email: "", customer_phone: "", requested_date: "", requested_time: "", customer_message: "" });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const data = await api.requestLiveViewing({ property_id: property.id, ...form });
      setResult(data);
    } catch (err) {
      setError(err.data ? JSON.stringify(err.data) : "Could not submit your request. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="live-viewing-confirmation">
        <p>✅ Your live viewing request has been sent to the agency. Status: {result.status}.</p>
        <p>We'll notify you at the contact details you provided once the agent responds.</p>
      </div>
    );
  }

  return (
    <form className="live-viewing-form" onSubmit={submit}>
      <h3>Request a Live Viewing</h3>
      <p className="hint">
        A real person from the agency will walk through the property live over video, in real time — not a
        pre-recorded clip.
      </p>
      <input required placeholder="Your name" value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} />
      <input placeholder="Email" type="email" value={form.customer_email} onChange={(e) => setForm({ ...form, customer_email: e.target.value })} />
      <input placeholder="Phone" value={form.customer_phone} onChange={(e) => setForm({ ...form, customer_phone: e.target.value })} />
      <label>
        Preferred date
        <input required type="date" value={form.requested_date} onChange={(e) => setForm({ ...form, requested_date: e.target.value })} />
      </label>
      <label>
        Preferred time (optional — earliest available if blank)
        <input type="time" value={form.requested_time} onChange={(e) => setForm({ ...form, requested_time: e.target.value })} />
      </label>
      <textarea
        placeholder="I would like to see the living room, kitchen, bedrooms and surrounding environment."
        value={form.customer_message}
        onChange={(e) => setForm({ ...form, customer_message: e.target.value })}
      />
      {error && <p className="status-message status-message--error">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "Sending…" : "Send Request"}
      </button>
    </form>
  );
}

function EnquiryForm({ property }) {
  const [form, setForm] = useState({ customer_name: "", customer_email: "", customer_phone: "", message: "", consent_given: false });
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.submitLead({
        property_id: property.id,
        agency: property.agency.id,
        source_channel: "PROPERTY_ENQUIRY_FORM",
        ...form,
      });
      setSent(true);
    } catch (err) {
      setError(err.data ? JSON.stringify(err.data) : "Could not send your enquiry.");
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) return <p className="status-message">✅ Your enquiry has been referred to {property.agency.name}. They'll be in touch directly.</p>;

  return (
    <form className="enquiry-form" onSubmit={submit}>
      <h3>Submit an enquiry</h3>
      <input required placeholder="Your name" value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} />
      <input placeholder="Email" type="email" value={form.customer_email} onChange={(e) => setForm({ ...form, customer_email: e.target.value })} />
      <input placeholder="Phone" value={form.customer_phone} onChange={(e) => setForm({ ...form, customer_phone: e.target.value })} />
      <textarea placeholder="Your message" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
      <label className="checkbox-field">
        <input type="checkbox" checked={form.consent_given} onChange={(e) => setForm({ ...form, consent_given: e.target.checked })} />
        I agree to my contact details being shared with this agency so they can respond to my enquiry.
      </label>
      {error && <p className="status-message status-message--error">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "Sending…" : "Submit Enquiry"}
      </button>
      <p className="hint">This enquiry is referred to the agency — the platform does not process the transaction itself.</p>
    </form>
  );
}

export default function PropertyDetailPage() {
  const { id } = useParams();
  const [property, setProperty] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState(null);

  useEffect(() => {
    api
      .getProperty(id)
      .then(setProperty)
      .catch(() => setError("Could not load this property."));
  }, [id]);

  if (error) return <p className="status-message status-message--error">{error}</p>;
  if (!property) return <p className="status-message">Loading…</p>;

  return (
    <div className="property-detail">
      <div className="property-detail__gallery">
        {property.images && property.images.length > 0 ? (
          property.images.map((img) => <img key={img.id} src={img.image_url} alt={img.caption || property.title} />)
        ) : (
          <div className="property-card__image-placeholder">No photos available for this listing yet.</div>
        )}
      </div>

      <div className="property-detail__main">
        <h1>{property.title}</h1>
        <p className="property-detail__location">{property.location}</p>
        <p className="property-detail__price">{formatPrice(property.price, property.currency, property.price_period)}</p>

        {property.agency && (
          <Link to={`/agencies/${property.agency.slug}`} className="agency-link">
            <AgencyStatusBadge status={property.agency.verification_status} badges={property.agency.verification_badges} />
          </Link>
        )}
        <PropertyVerificationLine status={property.verification_status} />
        {property.is_stale && <p className="status-message status-message--warning">⚠ This listing has not been recently confirmed and may be stale.</p>}

        <dl className="property-detail__attrs">
          <div><dt>Type</dt><dd>{property.property_type}</dd></div>
          <div><dt>Bedrooms</dt><dd>{property.bedrooms ?? "–"}</dd></div>
          <div><dt>Bathrooms</dt><dd>{property.bathrooms ?? "–"}</dd></div>
          <div><dt>Toilets</dt><dd>{property.toilets ?? "–"}</dd></div>
          <div><dt>Furnished</dt><dd>{property.furnished_status}</dd></div>
        </dl>

        {property.amenities && property.amenities.length > 0 && (
          <div className="property-detail__amenities">
            <h3>Amenities</h3>
            <ul>
              {property.amenities.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </div>
        )}

        <p className="property-detail__description">{property.description}</p>

        <div className="property-detail__actions">
          {property.agency?.phone_number && <a href={`tel:${property.agency.phone_number}`} className="btn">Call Agency</a>}
          {property.agency?.email && <a href={`mailto:${property.agency.email}`} className="btn">Email Agency</a>}
          {property.agency?.whatsapp_number && (
            <a href={`https://wa.me/${property.agency.whatsapp_number}`} target="_blank" rel="noreferrer" className="btn">WhatsApp</a>
          )}
          {property.agency?.website && (
            <a href={property.agency.website} target="_blank" rel="noreferrer" className="btn btn--secondary">Visit Agency Website</a>
          )}
          {property.live_viewing_available && (
            <button className="btn btn--primary" onClick={() => setTab("live_viewing")}>
              🎥 Request Live Viewing
            </button>
          )}
          <button className="btn btn--secondary" onClick={() => setTab("enquiry")}>
            Submit Enquiry
          </button>
        </div>

        {property.source_name && (
          <p className="hint">
            Source: {property.source_name}
            {property.source_url && (
              <>
                {" · "}
                <a href={property.source_url} target="_blank" rel="noreferrer noopener">
                  View original listing
                </a>
              </>
            )}
          </p>
        )}

        {tab === "live_viewing" && <LiveViewingRequestForm property={property} />}
        {tab === "enquiry" && <EnquiryForm property={property} />}
      </div>
    </div>
  );
}
