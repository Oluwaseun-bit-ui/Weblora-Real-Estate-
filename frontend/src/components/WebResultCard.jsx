function formatPhone(phone) {
  // +2348031234567 -> 0803 123 4567 (how Nigerians usually read numbers)
  const m = phone.match(/^\+234(\d{3})(\d{3})(\d{4})$/);
  return m ? `0${m[1]} ${m[2]} ${m[3]}` : phone;
}

export default function WebResultCard({ result }) {
  const { phones = [], emails = [], whatsapp = [] } = result.contacts || {};
  const hasContacts = phones.length || emails.length || whatsapp.length;

  return (
    <article className="web-result">
      <div className="web-result__header">
        <span className="web-result__site">{result.site}</span>
        <span className="status-pill status-pill--neutral" title="Found on the web. Weblora has not checked this agent.">
          Not verified
        </span>
      </div>
      <h3>
        <a href={result.url} target="_blank" rel="noreferrer noopener">
          {result.title}
        </a>
      </h3>
      {result.snippet && <p className="web-result__snippet">{result.snippet}</p>}

      <div className="web-result__actions">
        <a href={result.url} target="_blank" rel="noreferrer noopener" className="btn btn--secondary">
          Visit website
        </a>
        {phones.slice(0, 2).map((p) => (
          <a key={p} href={`tel:${p}`} className="btn">
            Call {formatPhone(p)}
          </a>
        ))}
        {whatsapp[0] && (
          <a href={`https://wa.me/${whatsapp[0]}`} target="_blank" rel="noreferrer noopener" className="btn">
            WhatsApp
          </a>
        )}
        {emails[0] && (
          <a href={`mailto:${emails[0]}`} className="btn">
            Email {emails[0]}
          </a>
        )}
      </div>
      {!hasContacts && <p className="hint">No contact details found on this page. Visit the website to reach the agent.</p>}
    </article>
  );
}
