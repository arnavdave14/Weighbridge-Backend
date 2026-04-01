import { create } from 'zustand'

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  login: (token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('admin_token'),
  isAuthenticated: !!localStorage.getItem('admin_token'),

  login: (token: string) => {
    localStorage.setItem('admin_token', token)
    set({ token, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('admin_token')
    set({ token: null, isAuthenticated: false })
  },
}))
