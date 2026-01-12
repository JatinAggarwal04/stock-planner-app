//frontend/src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { useWatchlistStore } from './context/WatchlistContext'
import { useEffect } from 'react'
import Login from './pages/Login'
import Signup from './pages/SignUp'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'
import Navbar from './components/layout/Navbar'
import TestAPI from './pages/TestAPI'
import BackendStatus from './components/BackendStatus'
function App() {
  const { user, loading } = useAuth()
  const { initialize } = useWatchlistStore()

  // Initialize watchlist when user logs in
  useEffect(() => {
    if (user) {
      initialize(user.id)
    }
  }, [user, initialize])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-950">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {user && <Navbar />}
      {/* Backend Status Indicator (Dev only) */}
      <BackendStatus />

      <Routes>
        <Route
          path="/"
          element={user ? <Navigate to="/dashboard" /> : <Login />}
        />
        <Route
          path="/signup"
          element={user ? <Navigate to="/dashboard" /> : <Signup />}
        />
        <Route path="/test-api" element={<TestAPI />} />

        <Route
          path="/dashboard"
          element={user ? <Dashboard /> : <Navigate to="/login" />}
        />
        <Route
          path="/stock/:symbol"
          element={user ? <StockDetail /> : <Navigate to="/login" />}
        />
        <Route
          path="/"
          element={<Navigate to={user ? "/dashboard" : "/login"} />}
        />
      </Routes>
    </div>
  )
}

export default App