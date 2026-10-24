import axios from "axios";

export const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// Attach token (added in Phase 1 login flow)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401 (added in Phase 1)
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err?.response?.status === 401 && !err.config.__retried) {
      // Phase 1: try refresh endpoint
    }
    return Promise.reject(err);
  }
);
