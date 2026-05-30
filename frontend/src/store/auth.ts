import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  user: { id: number; username: string; role: string } | null
  setToken: (token: string) => void
  setUser: (user: { id: number; username: string; role: string }) => void
  logout: () => void
  isAdmin: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null }),
      isAdmin: () => get().user?.role === 'admin',
    }),
    { name: 'nexus-auth' }
  )
)
