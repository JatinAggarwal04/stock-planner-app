//frontend/src/components/BackendStatus.jsx
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'

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
      <div className="fixed bottom-4 left-4 bg-danger-100 dark:bg-danger-900/20 border border-danger-500 text-danger-700 dark:text-danger-400 px-4 py-2 rounded-lg text-sm">
        ⚠️ Backend Offline
      </div>
    )
  }

  return null
}