import { useState } from 'react'
import { stockService } from '../services/stockService'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'

export default function TestAPI() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const testAPI = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      console.log('Testing API call to RELIANCE.NS')
      const data = await stockService.analyzeStock('RELIANCE.NS')
      console.log('Success:', data)
      setResult(data)
    } catch (err) {
      console.error('Error:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-dark-bg p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">API Test Page</h1>

        <Card className="p-6 mb-6">
          <Button onClick={testAPI} disabled={loading}>
            {loading ? 'Testing...' : 'Test API Call (RELIANCE.NS)'}
          </Button>
        </Card>

        {error && (
          <Card className="p-6 mb-6 border-danger-500">
            <h3 className="text-lg font-bold text-danger-600 mb-2">Error:</h3>
            <pre className="text-sm text-slate-700 dark:text-slate-300 overflow-auto">
              {error}
            </pre>
          </Card>
        )}

        {result && (
          <Card className="p-6">
            <h3 className="text-lg font-bold text-success-600 mb-2">Success! ✓</h3>
            <pre className="text-xs text-slate-700 dark:text-slate-300 overflow-auto max-h-96 bg-slate-100 dark:bg-slate-800 p-4 rounded">
              {JSON.stringify(result, null, 2)}
            </pre>
          </Card>
        )}
      </div>
    </div>
  )
}