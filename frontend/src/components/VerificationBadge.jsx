const STATUS_LABEL = {
  DISCOVERED: "Discovered — not yet reviewed",
  PENDING_REVIEW: "Verification pending",
  VERIFICATION_IN_PROGRESS: "Verification in progress",
  VERIFIED: "Verified agency",
  REJECTED: "Verification rejected",
  SUSPENDED: "Suspended",
  EXPIRED_RECHECK_REQUIRED: "Verification expired — recheck required",
};

const PROPERTY_STATUS_LABEL = {
  SOURCE_CONFIRMED: "Source confirmed",
  AGENCY_PROVIDED: "Agency-provided information",
  INDEPENDENTLY_VERIFIED: "Independently verified",
  PENDING_REVIEW: "Pending review",
  REMOVED: "Removed",
  STALE: "May be stale — pending recheck",
};

export function AgencyStatusBadge({ status, badges = [] }) {
  const isVerified = status === "VERIFIED";
  return (
    <div className="verification-badge-group">
      <span className={`status-pill ${isVerified ? "status-pill--verified" : "status-pill--neutral"}`}>
        {isVerified ? "✓ " : ""}
        {STATUS_LABEL[status] || status}
      </span>
      {badges.map((b) => (
        <span key={b} className="badge badge--evidence" title="Each badge names exactly what was checked.">
          {b}
        </span>
      ))}
    </div>
  );
}

export function PropertyVerificationLine({ status }) {
  return <span className="property-verification-line">{PROPERTY_STATUS_LABEL[status] || status}</span>;
}
