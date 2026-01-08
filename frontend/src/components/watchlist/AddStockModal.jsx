//frontend/src/components/watchlist/AddStockModal.jsx
import { useState, useCallback, useRef, useEffect } from 'react'
import { Search, TrendingUp } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Input from '../ui/Input'
import { useWatchlistStore } from '../../context/WatchlistContext'
import { POPULAR_STOCKS } from '../../utils/constants'
import { stockService } from '../../services/stockService'
import toast from 'react-hot-toast'

// Debounce utility
const debounce = (func, wait) => {
  let timeout
  return (...args) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

export default function AddStockModal({ isOpen, onClose }) {
  const [symbol, setSymbol] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [showResults, setShowResults] = useState(false)

  const { addToWatchlist, isInWatchlist } = useWatchlistStore()

  // Clear state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSymbol('')
      setSearchResults([])
      setShowResults(false)
    }
  }, [isOpen])

  const searchStocks = async (query) => {
    if (!query || query.length < 2) {
      setSearchResults([])
      setShowResults(false)
      return
    }

    setIsLoading(true)
    setShowResults(true)
    try {
      const results = await stockService.searchStocks(query)
      setSearchResults(results)
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const debouncedSearch = useCallback(debounce(searchStocks, 500), [])

  const handleSearch = (value) => {
    debouncedSearch(value)
    if (!value) setShowResults(false)
  }

  const handleSelectStock = (stock) => {
    handleAdd(stock.symbol)
    setSymbol('')
    setShowResults(false)
  }

  const handleAdd = (stockSymbol) => {
    const formattedSymbol = stockSymbol.endsWith('.NS') ? stockSymbol : `${stockSymbol}.NS`

    if (isInWatchlist(formattedSymbol)) {
      toast.error('Stock already in watchlist')
      return
    }

    addToWatchlist(formattedSymbol)
    toast.success(`${formattedSymbol.replace('.NS', '')} added to watchlist`)
    setSymbol('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (symbol.trim()) {
      handleAdd(symbol.trim().toUpperCase())
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Stock to Watchlist">
      <form onSubmit={handleSubmit} className="mb-6 relative">
        <Input
          icon={Search}
          value={symbol}
          onChange={(e) => {
            setSymbol(e.target.value)
            handleSearch(e.target.value)
          }}
          placeholder="Search stocks (e.g., Tata, Reliance)"
          className="mb-3"
          autoComplete="off"
        />

        {/* Search Results Dropdown */}
        {showResults && (
          <div className="absolute z-10 w-full mt-1 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 max-h-60 overflow-y-auto">
            {isLoading ? (
              <div className="p-3 text-center text-sm text-slate-500">Searching...</div>
            ) : searchResults.length > 0 ? (
              <ul>
                {searchResults.map((result) => (
                  <li key={result.symbol}>
                    <button
                      type="button"
                      onClick={() => handleSelectStock(result)}
                      className="w-full text-left p-3 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors flex justify-between items-center group"
                    >
                      <div>
                        <div className="font-medium text-slate-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400">
                          {result.symbol.replace('.NS', '').replace('.BO', '')}
                        </div>
                        <div className="text-xs text-slate-500 truncate max-w-[200px]">
                          {result.name}
                        </div>
                      </div>
                      <span className="text-xs text-slate-400 bg-slate-100 dark:bg-slate-900 px-2 py-1 rounded">
                        {result.exchange}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : symbol.length >= 2 ? (
              <div className="p-3 text-center text-sm text-slate-500">No results found</div>
            ) : null}
          </div>
        )}

        <Button type="submit" className="w-full mt-2">
          Add to Watchlist
        </Button>
      </form>

      {/* Popular Stocks */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
          Popular Stocks
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {POPULAR_STOCKS.map((stock) => {
            const inWatchlist = isInWatchlist(stock)
            return (
              <button
                key={stock}
                onClick={() => !inWatchlist && handleAdd(stock)}
                disabled={inWatchlist}
                className={`p-3 rounded-lg border-2 text-left transition-all ${inWatchlist
                  ? 'border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 cursor-not-allowed opacity-50'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/10'
                  }`}
              >
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-primary-600" />
                  <span className="font-mono font-medium text-sm text-slate-900 dark:text-white">
                    {stock.replace('.NS', '')}
                  </span>
                </div>
                {inWatchlist && (
                  <div className="text-xs text-slate-500 mt-1">In watchlist</div>
                )}
              </button>
            )
          })}
        </div>
      </div>

      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-200 dark:border-blue-800">
        <p className="text-sm text-blue-900 dark:text-blue-300">
          <strong>Tip:</strong> NSE stocks end with .NS (e.g., RELIANCE.NS).
          BSE stocks end with .BO (e.g., RELIANCE.BO)
        </p>
      </div>
    </Modal>
  )
}