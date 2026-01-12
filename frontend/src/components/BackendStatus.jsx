//frontend/src/components/BackendStatus.jsx
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
//.
export default function BackendStatus() {
  const { data, isError } = useQuery({
    queryKey: ['backend-status'],
    queryFn: async () => {
      const response = await api.get('/')
      return response.data
    },
    retry: false,
  })

  if (isError) {
    return (
      <div className="fixed bottom-4 left-4 bg-danger-100 dark:bg-danger-900/20 border border-danger-500 text-danger-700 dark:text-danger-400 px-4 py-2 rounded-lg text-sm shadow-lg z-50">
        <div className="font-bold flex items-center gap-2">
          ⚠️ Backend Connection Failed
        </div>
        <div className="text-xs mt-1 opacity-80 font-mono">
          Target: {api.defaults.baseURL}
        </div>
      </div>
    )
  }

  return (
    <div className="fixed bottom-4 left-4 bg-emerald-100 dark:bg-emerald-900/20 border border-emerald-500 text-emerald-700 dark:text-emerald-400 px-4 py-2 rounded-lg text-sm shadow-lg z-50">
      <div className="font-bold flex items-center gap-2">
        ✅ Backend Connected
      </div>
      <div className="text-xs mt-1 opacity-80 font-mono">
        Target: {api.defaults.baseURL}
      </div>
    </div>
  )
}
