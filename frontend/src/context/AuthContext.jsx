//frontend/src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect } from 'react'
import { supabase } from '../services/supabase'
import { useWatchlistStore } from './WatchlistContext'
import toast from 'react-hot-toast'

const AuthContext = createContext({})

// Users must sign in again 12 hours after their last sign-in, even though Supabase keeps refreshing the token
export const MAX_SESSION_MS = 12 * 60 * 60 * 1000

export function isSessionExpired(user, now = Date.now()) {
  const signedInAt = Date.parse(user?.last_sign_in_at ?? '')
  return Number.isFinite(signedInAt) && now - signedInAt > MAX_SESSION_MS
}

// Returns the user if the session is still valid; otherwise signs out and returns null
export async function enforceSessionLimit(session) {
  const user = session?.user ?? null
  if (!isSessionExpired(user)) return user
  await supabase.auth.signOut()
  toast('Your session has expired. Please sign in again.')
  return null
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check active sessions
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      setUser(await enforceSessionLimit(session))
      setLoading(false)
    })

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT') {
        setUser(null)
        useWatchlistStore.getState().clearWatchlist()
        return
      }
      // Deferred: Supabase advises against calling auth methods (signOut) inside this callback
      setTimeout(() => enforceSessionLimit(session).then(setUser), 0)
    })

    return () => subscription.unsubscribe()
  }, [])

  // While signed in, re-check every minute and whenever the tab becomes visible again
  // (timers are paused in background tabs and on phones)
  useEffect(() => {
    if (!user) return

    const check = () => {
      if (isSessionExpired(user)) {
        supabase.auth.getSession().then(({ data: { session } }) => enforceSessionLimit(session))
      }
    }
    const onVisible = () => document.visibilityState === 'visible' && check()

    const timer = setInterval(check, 60 * 1000)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [user])

  const signUp = async (email, password, fullName) => {
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          },
        },
      })

      if (error) throw error

      toast.success('Account created! Please check your email to verify.')
      return { data, error: null }
    } catch (error) {
      toast.error(error.message)
      return { data: null, error }
    }
  }

  const signIn = async (email, password) => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) throw error

      toast.success('Welcome back!')
      return { data, error: null }
    } catch (error) {
      toast.error(error.message)
      return { data: null, error }
    }
  }

  const signInWithGoogle = async () => {
    try {
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/dashboard`,
        },
      })

      if (error) throw error
      return { data, error: null }
    } catch (error) {
      toast.error(error.message)
      return { data: null, error }
    }
  }



  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut()
      if (error) throw error
      toast.success('Signed out successfully')
    } catch (error) {
      toast.error(error.message)
    }
  }

  const value = {
    user,
    loading,
    signUp,
    signIn,
    signInWithGoogle,
    signOut,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}