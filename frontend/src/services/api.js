//frontend/src/services/api.js
import axios from 'axios'
import toast from 'react-hot-toast'
import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// The backend only serves signed-in users: send the Supabase access token with every request
export async function authHeaders() {
  const { data: { session } } = await supabase.auth.getSession()
  return session ? { Authorization: `Bearer ${session.access_token}` } : {}
}

// The backend rejected the session (expired after 12 hours, or invalid): sign out so the user logs in again
export async function handleUnauthorized() {
  await supabase.auth.signOut()
  toast('Your session has expired. Please sign in again.')
}

const api = axios.create({
  baseURL: API_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  async (config) => {
    Object.assign(config.headers, await authHeaders())
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.status, error.config?.url, error.message)
    
    if (error.response?.status === 401) {
      handleUnauthorized()
    } else if (error.response?.status === 404) {
      console.error('Stock not found:', error.config?.url)
    } else if (error.response?.status === 500) {
      console.error('Server error:', error.response?.data)
    } else if (error.code === 'ECONNABORTED') {
      console.error('Request timeout')
    } else if (!error.response) {
      console.error('Network error - backend might be offline')
    }
    
    return Promise.reject(error)
  }
)

export default api