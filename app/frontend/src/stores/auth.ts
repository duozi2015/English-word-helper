import { create } from 'zustand'
import axios from 'axios'
import { api, clearTokens, getToken, setTokens } from '../lib/api'

export interface User {
  id: number
  username: string
  display_name: string
  role: string
}

interface AuthState {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  fetchMe: () => Promise<void>
  logout: () => void
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: !!getToken(),

  login: async (username, password) => {
    const r = await axios.post('/words/api/auth/login', { username, password })
    setTokens(r.data.access_token, r.data.refresh_token)
    const me = await api.get('/auth/me')
    set({ user: me.data })
  },

  fetchMe: async () => {
    if (!getToken()) {
      set({ user: null, loading: false })
      return
    }
    try {
      const r = await api.get('/auth/me')
      set({ user: r.data, loading: false })
    } catch {
      set({ user: null, loading: false })
    }
  },

  logout: () => {
    clearTokens()
    set({ user: null })
  },
}))
