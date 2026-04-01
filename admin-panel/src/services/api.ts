import axios from 'axios'

const api = axios.create({
  // In dev, Vite proxies /admin → localhost:8000/admin
  // In prod, set VITE_API_BASE in .env
  baseURL: (import.meta as any).env?.VITE_API_BASE ?? '/admin',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('admin_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
