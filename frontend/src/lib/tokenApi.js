import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const API_KEY_STORAGE = "tokenscope.api_key";

export const getApiKey = () => {
  try {
    return localStorage.getItem(API_KEY_STORAGE) || "";
  } catch (e) {
    return "";
  }
};

export const setApiKey = (key) => {
  try {
    if (key) localStorage.setItem(API_KEY_STORAGE, key);
    else localStorage.removeItem(API_KEY_STORAGE);
  } catch (e) {
    /* ignore */
  }
};

export const api = axios.create({
  baseURL: API,
  timeout: 30000,
});

// Inject X-API-Key on every request when one is stored.
api.interceptors.request.use((config) => {
  const k = getApiKey();
  if (k) {
    config.headers = config.headers || {};
    config.headers["X-API-Key"] = k;
  }
  return config;
});

export const fetchAuthStatus = () => api.get(`/auth/check`).then((r) => r.data);

export const fetchSummary = (days = 30) =>
  api.get(`/usage/summary`, { params: { days } }).then((r) => r.data);

export const fetchUsage = (params = {}) =>
  api.get(`/usage`, { params }).then((r) => r.data);

export const fetchLive = () => api.get(`/usage/live`).then((r) => r.data);

export const fetchThreshold = () => api.get(`/threshold`).then((r) => r.data);

export const saveThreshold = (data) =>
  api.put(`/threshold`, data).then((r) => r.data);

export const uploadFile = (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return api
    .post(`/usage/import`, fd, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const createUsage = (payload) =>
  api.post(`/usage`, payload).then((r) => r.data);

export const deleteUsage = (id) => api.delete(`/usage/${id}`).then((r) => r.data);

export const clearAllUsage = () => api.delete(`/usage`).then((r) => r.data);

export const seedDemo = () => api.post(`/usage/seed`).then((r) => r.data);

export const TOOL_LABEL = {
  claude_api: "Claude API",
  codex: "Codex",
  antigravity: "Antigravity",
};

export const TOOL_COLORS = {
  claude_api: "#FFFFFF",
  codex: "#A1A1AA",
  antigravity: "#FFCC00",
};

export const formatNumber = (n) => {
  if (n === null || n === undefined) return "—";
  const num = Number(n);
  if (Number.isNaN(num)) return "—";
  if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(2) + "B";
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(2) + "M";
  if (num >= 1_000) return (num / 1_000).toFixed(2) + "k";
  return num.toLocaleString("en-US");
};

export const formatCost = (n) => {
  const num = Number(n || 0);
  return "$" + num.toFixed(num < 1 ? 4 : 2);
};
