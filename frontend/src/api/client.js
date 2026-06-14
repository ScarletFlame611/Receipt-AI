// API-клиент: хранит JWT и пробрасывает его в заголовок Authorization.
// Пути относительные — в dev их проксирует Vite на FastAPI (см. vite.config.js).

const TOKEN_KEY = 'token'
let token = localStorage.getItem(TOKEN_KEY)

export function setToken(value) {
  token = value
  if (value) localStorage.setItem(TOKEN_KEY, value)
  else localStorage.removeItem(TOKEN_KEY)
}
export function getToken() {
  return token
}

async function request(path, { method = 'GET', json, form, body, headers = {} } = {}) {
  const opts = { method, headers: { ...headers } }
  if (token) opts.headers.Authorization = `Bearer ${token}`

  if (json !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(json)
  } else if (form) {
    opts.headers['Content-Type'] = 'application/x-www-form-urlencoded'
    opts.body = new URLSearchParams(form).toString()
  } else if (body) {
    opts.body = body // FormData (multipart) — Content-Type выставит браузер
  }

  const res = await fetch(path, opts)
  if (res.status === 204) return null

  let data = null
  const text = await res.text()
  if (text) {
    try { data = JSON.parse(text) } catch { data = text }
  }
  if (!res.ok) {
    const detail = data?.detail || res.statusText
    const err = new Error(Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : detail)
    err.status = res.status
    throw err
  }
  return data
}

export const api = {
  // --- auth ---
  login: (email, password) =>
    request('/auth/login', { method: 'POST', form: { username: email, password } }),
  register: (email, password) =>
    request('/auth/register', { method: 'POST', json: { email, password } }),
  me: () => request('/auth/me'),
  logout: () => request('/auth/logout', { method: 'POST' }),
  requestReset: (email) =>
    request('/auth/password-reset/request', { method: 'POST', json: { email } }),
  confirmReset: (resetToken, newPassword) =>
    request('/auth/password-reset/confirm', {
      method: 'POST',
      json: { token: resetToken, new_password: newPassword },
    }),

  // --- receipts ---
  uploadReceipt: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('/receipts', { method: 'POST', body: fd })
  },
  listReceipts: (limit = 50, offset = 0) =>
    request(`/receipts?limit=${limit}&offset=${offset}`),
  getReceipt: (id) => request(`/receipts/${id}`),
  updateReceipt: (id, fields) => request(`/receipts/${id}`, { method: 'PUT', json: fields }),
  reviewReceipt: (id, payload) =>
    request(`/receipts/${id}/review`, { method: 'PUT', json: payload }),
  deleteReceipt: (id) => request(`/receipts/${id}`, { method: 'DELETE' }),

  // --- analytics ---
  summary: () => request('/analytics/summary'),
  timeline: () => request('/analytics/timeline'),
  topMerchants: (limit = 10) => request(`/analytics/top-merchants?limit=${limit}`),
  topGoods: (limit = 10) => request(`/analytics/top-goods?limit=${limit}`),
  listBudgets: () => request('/analytics/budgets'),
  createBudget: (payload) => request('/analytics/budgets', { method: 'POST', json: payload }),
  deleteBudget: (id) => request(`/analytics/budgets/${id}`, { method: 'DELETE' }),
  listGoals: () => request('/analytics/goals'),
  createGoal: (payload) => request('/analytics/goals', { method: 'POST', json: payload }),
  updateGoal: (id, payload) => request(`/analytics/goals/${id}`, { method: 'PUT', json: payload }),
  deleteGoal: (id) => request(`/analytics/goals/${id}`, { method: 'DELETE' }),

  // --- meta ---
  categories: () => request('/categories'),

  // --- admin ---
  adminUsers: () => request('/admin/users'),
  adminBlock: (id) => request(`/admin/users/${id}/block`, { method: 'POST' }),
  adminUnblock: (id) => request(`/admin/users/${id}/unblock`, { method: 'POST' }),
  adminMetrics: () => request('/admin/metrics'),
}
