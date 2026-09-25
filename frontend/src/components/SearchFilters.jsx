const PROPERTY_TYPES = ["APARTMENT", "HOUSE", "DUPLEX", "BUNGALOW", "TERRACE", "LAND", "SHORTLET", "COMMERCIAL", "OTHER"];
const TRANSACTION_TYPES = ["RENT", "BUY", "SHORTLET"];
const FURNISHED = ["FURNISHED", "SEMI_FURNISHED", "UNFURNISHED"];

export default function SearchFilters({ filters, onChange, onSubmit }) {
  const set = (key) => (e) => onChange({ ...filters, [key]: e.target.value });

  return (
    <form
      className="search-filters"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <input
        type="text"
        placeholder="Location (e.g. Lekki, Ikeja, Ajah)"
        value={filters.location || ""}
        onChange={set("location")}
      />

      <select value={filters.transaction_type || ""} onChange={set("transaction_type")}>
        <option value="">Rent / Buy / Shortlet</option>
        {TRANSACTION_TYPES.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>

      <select value={filters.property_type || ""} onChange={set("property_type")}>
        <option value="">Property type</option>
        {PROPERTY_TYPES.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>

      <input type="number" min="0" placeholder="Bedrooms" value={filters.bedrooms || ""} onChange={set("bedrooms")} />
      <input type="number" min="0" placeholder="Bathrooms" value={filters.bathrooms || ""} onChange={set("bathrooms")} />

      <input type="number" min="0" placeholder="Min price (₦)" value={filters.min_price || ""} onChange={set("min_price")} />
      <input type="number" min="0" placeholder="Max price (₦)" value={filters.max_price || ""} onChange={set("max_price")} />

      <select value={filters.furnished_status || ""} onChange={set("furnished_status")}>
        <option value="">Furnished / Unfurnished</option>
        {FURNISHED.map((f) => (
          <option key={f} value={f}>
            {f}
          </option>
        ))}
      </select>

      <label className="checkbox-field">
        <input
          type="checkbox"
          checked={filters.verified_agency === "true"}
          onChange={(e) => onChange({ ...filters, verified_agency: e.target.checked ? "true" : "" })}
        />
        Verified agencies only
      </label>

      <select value={filters.sort || "relevance"} onChange={set("sort")}>
        <option value="relevance">Sort: Relevance</option>
        <option value="newest">Sort: Newest</option>
        <option value="price_asc">Sort: Price (low to high)</option>
        <option value="price_desc">Sort: Price (high to low)</option>
      </select>

      <button type="submit">Search</button>
    </form>
  );
}
