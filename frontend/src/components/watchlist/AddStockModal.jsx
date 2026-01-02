import { useState } from 'react'
import { Search, TrendingUp } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Input from '../ui/Input'
import { useWatchlistStore } from '../../context/WatchlistContext'
import { POPULAR_STOCKS } from '../../utils/constants'
import toast from 'react-hot-toast'

export default function AddStockModal({ isOpen, onClose }) {
  const [symbol, setSymbol] = useState('')
  const { addToWatchlist, isInWatchlist } = useWatchlistStore()

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
      <form onSubmit={handleSubmit} className="mb-6">
        <Input
          icon={Search}
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Enter stock symbol (e.g., RELIANCE, TCS)"
          className="mb-3"
        />
        <Button type="submit" className="w-full">
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
                className={`p-3 rounded-lg border-2 text-left transition-all ${
                  inWatchlist
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