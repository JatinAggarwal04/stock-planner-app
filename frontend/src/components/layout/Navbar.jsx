//frontend/src/components/layout/Navbar.jsx
import { Link } from 'react-router-dom'
import { TrendingUp, LogOut, User, Settings } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import ThemeToggle from './ThemeToggle'
import { motion } from 'framer-motion'
import { useState } from 'react'
//.
export default function Navbar() {
  const { user, signOut } = useAuth()
  const [showDropdown, setShowDropdown] = useState(false)

  const getUserInitial = () => {
    return user?.email?.charAt(0).toUpperCase() || 'U'
  }

  return (
    <nav className="sticky top-0 z-50 bg-white dark:bg-dark-surface border-b border-slate-200 dark:border-dark-border shadow-sm dark:shadow-none">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-3 group">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-slate-900 dark:text-white">
              TradeWise
            </span>
          </Link>

          {/* Right Section */}
          <div className="flex items-center gap-4">
            <ThemeToggle />

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                  {getUserInitial()}
                </div>
              </button>

              {/* Dropdown */}
              {showDropdown && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowDropdown(false)}
                  ></div>
                  
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="absolute right-0 mt-2 w-56 bg-white dark:bg-dark-surface rounded-xl shadow-lg border border-slate-200 dark:border-dark-border overflow-hidden z-50"
                  >
                    <div className="px-4 py-3 border-b border-slate-200 dark:border-dark-border">
                      <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                        {user?.email}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Free Plan
                      </p>
                    </div>

                    <div className="py-2">
                      <button className="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                        <User className="w-4 h-4" />
                        <span>Profile</span>
                      </button>
                      
                      <button className="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                        <Settings className="w-4 h-4" />
                        <span>Settings</span>
                      </button>
                    </div>

                    <div className="border-t border-slate-200 dark:border-dark-border py-2">
                      <button
                        onClick={signOut}
                        className="w-full flex items-center gap-3 px-4 py-2 text-sm text-danger-600 hover:bg-danger-50 dark:hover:bg-danger-900/10 transition-colors"
                      >
                        <LogOut className="w-4 h-4" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </motion.div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}
