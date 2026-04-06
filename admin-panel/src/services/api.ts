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
  console.log(`[API: Request] ${config.method?.toUpperCase()} ${config.url}`)
  return config
})

api.interceptors.response.use(
  (res) => {
    console.log(`[API: Success] ${res.config.method?.toUpperCase()} ${res.config.url}`)
    return res
  },
  (err) => {
    const status = err.response?.status
    const url = err.config?.url
    const method = err.config?.method?.toUpperCase()
    console.error(`[API: Error] ${method} ${url} | Status: ${status} | Message: ${err.message}`, err.response?.data)

    if (status === 401) {
      localStorage.removeItem('admin_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
