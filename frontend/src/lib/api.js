// Small fetch wrapper for the Trackly Django API.
// Handles the JWT access token and refreshes it (rotating refresh tokens) on 401.

const BASE = import.meta.env.VITE_API_BASE || '/api'
const ACCESS_KEY = 'trackly_access'
const REFRESH_KEY = 'trackly_refresh'

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set({ access, refresh }) {
    if (access) localStorage.setItem(ACCESS_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

// Turn any DRF error payload into one readable string.
function extractMessage(data, fallback) {
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (data.message) return data.message
  if (data.detail) return data.detail
  if (data.error) return data.error
  if (typeof data === 'object') {
    const parts = []
    for (const [field, val] of Object.entries(data)) {
      const text = Array.isArray(val) ? val.join(' ') : String(val)
      parts.push(field === 'non_field_errors' ? text : `${field}: ${text}`)
    }
    if (parts.length) return parts.join('\n')
  }
  return fallback
}

async function parse(res) {
  if (res.status === 204) return null
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

let refreshing = null

async function refreshAccess() {
  if (!tokens.refresh) throw new ApiError('Session expired', 401)
  if (!refreshing) {
    refreshing = fetch(`${BASE}/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: tokens.refresh }),
    })
      .then(async (res) => {
        const data = await parse(res)
        if (!res.ok) throw new ApiError('Session expired', 401, data)
        // ROTATE_REFRESH_TOKENS is on, so a new refresh token comes back too.
        tokens.set({ access: data.access, refresh: data.refresh })
      })
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

export async function request(path, { method = 'GET', body, auth = true } = {}) {
  const doFetch = () => {
    const headers = { 'Content-Type': 'application/json' }
    if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`
    return fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  }

  let res = await doFetch()

  if (res.status === 401 && auth && tokens.refresh) {
    try {
      await refreshAccess()
      res = await doFetch()
    } catch (err) {
      tokens.clear()
      window.dispatchEvent(new Event('trackly:logout'))
      throw err
    }
  }

  const data = await parse(res)
  if (!res.ok) {
    throw new ApiError(extractMessage(data, `Request failed (${res.status})`), res.status, data)
  }
  return data
}

export const api = {
  register: (email, password) =>
    request('/register/', { method: 'POST', body: { email, password }, auth: false }),
  login: (email, password) =>
    request('/login/', { method: 'POST', body: { email, password }, auth: false }),
  logout: (refresh) => request('/logout/', { method: 'POST', body: { refresh } }),

  listMonitors: () => request('/monitor/'),
  createMonitor: (url, check_interval) =>
    request('/monitor/', { method: 'POST', body: { url, check_interval } }),
  getMonitor: (id) => request(`/monitor/${id}/`),
  updateMonitor: (id, patch) => request(`/monitor/${id}/`, { method: 'PATCH', body: patch }),
  deleteMonitor: (id) => request(`/monitor/${id}/`, { method: 'DELETE' }),
  getChanges: (id) => request(`/monitor/${id}/changes/`),
}
