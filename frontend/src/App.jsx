//frontend/src/App.jsx
import { Suspense, lazy, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { useWatchlistStore } from './context/WatchlistContext'
import BackendStatus from './components/BackendStatus'
import Navbar from './components/layout/Navbar'

// Lazy Load Pages
const Login = lazy(() => import('./pages/Login'))
const Signup = lazy(() => import('./pages/SignUp'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const StockDetail = lazy(() => import('./pages/StockDetail'))
const TestAPI = lazy(() => import('./pages/TestAPI'))

// Loading Component
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-950">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
  </div>
)

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
    return <PageLoader />
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {user && <Navbar />}
      {/* Backend Status Indicator (Dev only) */}
      <BackendStatus />

      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Public Routes */}
          <Route
            path="/login"
            element={user ? <Navigate to="/dashboard" /> : <Login />}
          />
          <Route
            path="/signup"
            element={user ? <Navigate to="/dashboard" /> : <Signup />}
          />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={user ? <Dashboard /> : <Navigate to="/login" />}
          />
          <Route
            path="/stock/:symbol"
            element={user ? <StockDetail /> : <Navigate to="/login" />}
          />

          {/* Test Route */}
          <Route path="/test-api" element={<TestAPI />} />

          {/* Root Redirect */}
          <Route
            path="/"
            element={<Navigate to={user ? "/dashboard" : "/login"} replace />}
          />

          {/* Catch all - 404 to Dashboard/Login */}
          <Route
            path="*"
            element={<Navigate to={user ? "/dashboard" : "/login"} replace />}
          />
        </Routes>
      </Suspense>
    </div>
  )
}

export default App