import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, tokens } from './api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [isAuthed, setIsAuthed] = useState(() => Boolean(tokens.access || tokens.refresh))

  // api.js fires this when a refresh fails, so we drop back to the login page.
  useEffect(() => {
    const onLogout = () => setIsAuthed(false)
    window.addEventListener('trackly:logout', onLogout)
    return () => window.removeEventListener('trackly:logout', onLogout)
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await api.login(email, password)
    tokens.set(data)
    setIsAuthed(true)
  }, [])

  const register = useCallback(async (email, password) => {
    const data = await api.register(email, password)
    tokens.set(data)
    setIsAuthed(true)
  }, [])

  const logout = useCallback(async () => {
    try {
      if (tokens.refresh) await api.logout(tokens.refresh)
    } catch {
      // Even if the server call fails we still sign the user out locally.
    }
    tokens.clear()
    setIsAuthed(false)
  }, [])

  const value = useMemo(
    () => ({ isAuthed, login, register, logout }),
    [isAuthed, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
