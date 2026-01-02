import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Mail, Lock, User, TrendingUp, Chrome, Apple } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Signup() {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { signUp, signInWithGoogle, signInWithApple } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    const { error } = await signUp(email, password, fullName)
    
    if (!error) {
      navigate('/dashboard')
    }
    
    setLoading(false)
  }

  const handleGoogleSignup = async () => {
    setLoading(true)
    await signInWithGoogle()
    setLoading(false)
  }

  const handleAppleSignup = async () => {
    setLoading(true)
    await signInWithApple()
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-success-600 via-success-700 to-emerald-900 p-12 items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-white rounded-full blur-3xl"></div>
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-white rounded-full blur-3xl"></div>
        </div>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="relative z-10 text-white max-w-lg"
        >
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center">
              <TrendingUp className="w-7 h-7 text-success-600" />
            </div>
            <h1 className="text-4xl font-bold">TradeWise</h1>
          </div>
          
          <h2 className="text-3xl font-bold mb-4">
            Start Your Smart Trading Journey
          </h2>
          <p className="text-lg text-emerald-100 mb-8">
            Join thousands of traders who trust TradeWise for data-driven insights 
            and AI-powered recommendations.
          </p>
          
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-lg font-bold">✓</span>
              </div>
              <div>
                <div className="font-semibold mb-1">Real-Time Analysis</div>
                <div className="text-emerald-100 text-sm">
                  Get instant insights with live price updates and market data
                </div>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-lg font-bold">✓</span>
              </div>
              <div>
                <div className="font-semibold mb-1">Personalized Recommendations</div>
                <div className="text-emerald-100 text-sm">
                  AI analyzes your positions and suggests optimal actions
                </div>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-lg font-bold">✓</span>
              </div>
              <div>
                <div className="font-semibold mb-1">24/7 AI Assistant</div>
                <div className="text-emerald-100 text-sm">
                  Chat with Gemini AI for instant answers to your questions
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Right Side - Signup Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="w-10 h-10 bg-success-600 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">TradeWise</h1>
          </div>

          <div className="mb-8">
            <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">
              Create your account
            </h2>
            <p className="text-slate-600 dark:text-slate-400">
              Get started with TradeWise in seconds
            </p>
          </div>

          {/* Social Signup */}
          <div className="space-y-3 mb-6">
            <button
              onClick={handleGoogleSignup}
              disabled={loading}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 border-2 border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
            >
              <Chrome className="w-5 h-5" />
              <span className="font-medium text-slate-700 dark:text-slate-300">
                Sign up with Google
              </span>
            </button>

            <button
              onClick={handleAppleSignup}
              disabled={loading}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 border-2 border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
            >
              <Apple className="w-5 h-5" />
              <span className="font-medium text-slate-700 dark:text-slate-300">
                Sign up with Apple
              </span>
            </button>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200 dark:border-slate-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-slate-50 dark:bg-dark-bg text-slate-500">
                Or sign up with email
              </span>
            </div>
          </div>

          {/* Email Signup Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  placeholder="John Doe"
                  className="w-full pl-11 pr-4 py-3 border-2 border-slate-200 dark:border-slate-700 rounded-xl focus:border-success-500 focus:ring-2 focus:ring-success-200 dark:focus:ring-success-900 outline-none transition-all bg-white dark:bg-dark-surface text-slate-900 dark:text-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="you@example.com"
                  className="w-full pl-11 pr-4 py-3 border-2 border-slate-200 dark:border-slate-700 rounded-xl focus:border-success-500 focus:ring-2 focus:ring-success-200 dark:focus:ring-success-900 outline-none transition-all bg-white dark:bg-dark-surface text-slate-900 dark:text-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  placeholder="••••••••"
                  className="w-full pl-11 pr-4 py-3 border-2 border-slate-200 dark:border-slate-700 rounded-xl focus:border-success-500 focus:ring-2 focus:ring-success-200 dark:focus:ring-success-900 outline-none transition-all bg-white dark:bg-dark-surface text-slate-900 dark:text-white"
                />
              </div>
              <p className="mt-1 text-xs text-slate-500">Must be at least 6 characters</p>
            </div>

            <label className="flex items-start gap-2 cursor-pointer">
              <input type="checkbox" required className="w-4 h-4 mt-1 rounded border-slate-300" />
              <span className="text-sm text-slate-600 dark:text-slate-400">
                I agree to the{' '}
                <a href="#" className="text-primary-600 hover:text-primary-700">
                  Terms of Service
                </a>{' '}
                and{' '}
                <a href="#" className="text-primary-600 hover:text-primary-700">
                  Privacy Policy
                </a>
              </span>
            </label>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-success-600 hover:bg-success-700 text-white font-semibold py-3 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-600 hover:text-primary-700 font-semibold">
              Sign in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}