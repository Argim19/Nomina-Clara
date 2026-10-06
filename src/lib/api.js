const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

async function request(path, options = {}) {
  const token = localStorage.getItem('nomina_token');
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) localStorage.removeItem('nomina_token');
    throw new Error(data.error || 'No fue posible completar la solicitud.');
  }
  return data;
}

export const api = {
  login: (credentials) => request('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  dashboard: () => request('/dashboard'),
  employees: () => request('/employees'),
  createEmployee: (payload) => request('/employees', { method: 'POST', body: JSON.stringify(payload) }),
  updateEmployee: (id, payload) => request(`/employees/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  payrolls: () => request('/payrolls'),
  createPayroll: (payload) => request('/payrolls', { method: 'POST', body: JSON.stringify(payload) }),
  deductions: () => request('/config/deductions'),
  prepareEmail: (id) => request(`/payrolls/${id}/email`, { method: 'POST' }),
};

