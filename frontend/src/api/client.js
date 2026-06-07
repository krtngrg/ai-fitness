const BASE = "/api";

let _refreshing = null;

async function request(path, options = {}, _retry = false) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (res.status === 204) return null;

  // On 401, try refreshing the token once
  if (res.status === 401 && !_retry && path !== "/users/auth/refresh/") {
    if (!_refreshing) {
      _refreshing = fetch(`${BASE}/users/auth/refresh/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      }).finally(() => { _refreshing = null; });
    }
    const refreshRes = await _refreshing;
    if (refreshRes.ok) {
      return request(path, options, true);
    }
    // Refresh failed — let the original 401 propagate
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const msg =
      data?.detail ||
      data?.non_field_errors?.[0] ||
      Object.values(data)?.[0]?.[0] ||
      `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return data;
}

// Auth
export const register = (body) =>
  request("/users/auth/register/", { method: "POST", body: JSON.stringify(body) });

export const login = (body) =>
  request("/users/auth/login/", { method: "POST", body: JSON.stringify(body) });

export const logout = () =>
  request("/users/auth/logout/", { method: "POST" });

export const getMe = () => request("/users/auth/me/");

export const refreshToken = () =>
  request("/users/auth/refresh/", { method: "POST" });

// Profile
export const getProfile = () => request("/fitness/profile/");
export const patchProfile = (body) =>
  request("/fitness/profile/", { method: "PATCH", body: JSON.stringify(body) });

// Plan generation
export const generatePlan = (body) =>
  request("/fitness/plans/generate/", { method: "POST", body: JSON.stringify(body) });

// Roadmaps
export const getRoadmaps = () => request("/fitness/roadmaps/");
export const getRoadmap = (id) => request(`/fitness/roadmaps/${id}/`);
export const getTodayWorkout = () => request("/fitness/roadmaps/today/");

// Sessions
export const startSession = (roadmap_day_id) =>
  request("/fitness/workout-sessions/start/", {
    method: "POST",
    body: JSON.stringify({ roadmap_day_id }),
  });

export const getSessions = () => request("/fitness/workout-sessions/");
export const getSession = (id) => request(`/fitness/workout-sessions/${id}/`);

export const saveAIResult = (session_id, body) =>
  request(`/fitness/workout-sessions/${session_id}/ai-result/`, {
    method: "POST",
    body: JSON.stringify(body),
  });

// Dashboard
export const getDashboard = () => request("/fitness/dashboard/");

// Body metrics
export const getBodyMetrics = () => request("/fitness/body-metrics/");
export const addBodyMetric = (body) =>
  request("/fitness/body-metrics/", { method: "POST", body: JSON.stringify(body) });

// Goals
export const getGoals = () => request("/fitness/goals/");
