const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const error = new Error(data?.detail || "Request failed");
    error.status = res.status;
    error.data = data;
    throw error;
  }
  return data;
}

export const api = {
  searchProperties: (params) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== "" && v !== undefined && v !== null)
    ).toString();
    return request(`/properties/${qs ? `?${qs}` : ""}`);
  },
  getProperty: (id) => request(`/properties/${id}/`),
  getAgency: (slug) => request(`/agencies/${slug}/`),
  submitLead: (payload) =>
    request(`/leads/`, { method: "POST", body: JSON.stringify(payload) }),
  requestLiveViewing: (payload) =>
    request(`/live-viewing/requests/`, { method: "POST", body: JSON.stringify(payload) }),
  getLiveViewingStatus: (id) => request(`/live-viewing/requests/${id}/status/`),
  joinLiveViewing: (id, accessToken) =>
    request(`/live-viewing/requests/${id}/join/`, {
      method: "POST",
      body: JSON.stringify({ access_token: accessToken }),
    }),
  getPublicConfig: () => request(`/config/`),
};
