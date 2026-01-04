//frontend/src/components/watchlist/StockCard.jsx
import { useNavigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, X, Volume2 } from 'lucide-react'
import { useWatchlistStore } from '../../context/WatchlistContext'
import { formatters } from '../../utils/formatters'
import Card from '../ui/Card'
import Badge from '../ui/Badge'
import { motion } from 'framer-motion'

export default function StockCard({ data }) {
  const navigate = useNavigate()
  const { removeFromWatchlist, getTrade } = useWatchlistStore()
  
  const trade = getTrade(data.symbol)
  const isPositive = data.change >= 0
  
  // Calculate user's P&L if they have a position
  const userPL = trade 
    ? {
        value: (data.price - trade.buyPrice) * trade.quantity,
        percentage: ((data.price - trade.buyPrice) / trade.buyPrice) * 100
      }
    : null

  const handleRemove = (e) => {
    e.stopPropagation()
    removeFromWatchlist(data.symbol)
  }

  const handleClick = () => {
    navigate(`/stock/${data.symbol}`)
  }

  if (data.error) {
    return (
      <Card className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="font-mono font-medium text-slate-900 dark:text-white">
            {data.symbol}
          </span>
          <button
            onClick={handleRemove}
            className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded transition-colors"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>
        <p className="text-sm text-danger-600">Failed to load data</p>
      </Card>
    )
  }

  return (
    <Card hover onClick={handleClick} className="p-4 relative group">
      {/* Remove Button */}
      <button
        onClick={handleRemove}
        className="absolute top-3 right-3 p-1.5 bg-white dark:bg-slate-800 hover:bg-danger-50 dark:hover:bg-danger-900/20 rounded-lg opacity-0 group-hover:opacity-100 transition-all shadow-sm"
      >
        <X className="w-4 h-4 text-slate-600 dark:text-slate-400 hover:text-danger-600" />
      </button>

      {/* Stock Symbol */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-mono font-semibold text-lg text-slate-900 dark:text-white">
            {data.symbol.replace('.NS', '')}
          </h3>
          {trade && (
            <Badge variant="primary" className="mt-1">
              Position Held
            </Badge>
          )}
        </div>
      </div>

      {/* Price */}
      <div className="mb-4">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-slate-900 dark:text-white">
            {formatters.currency(data.price)}
          </span>
          <div className={`flex items-center gap-1 ${isPositive ? 'text-success-600' : 'text-danger-600'}`}>
            {isPositive ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            <span className="text-sm font-semibold">
              {formatters.percentage(data.change_pct)}
            </span>
          </div>
        </div>
        <div className={`text-sm font-medium ${isPositive ? 'text-success-600' : 'text-danger-600'}`}>
          {isPositive ? '+' : ''}{formatters.currency(data.change)}
        </div>
      </div>

      {/* User P&L if position exists */}
      {userPL && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className={`mb-4 p-3 rounded-lg ${
            userPL.value >= 0 
              ? 'bg-success-50 dark:bg-success-900/10 border border-success-200 dark:border-success-800' 
              : 'bg-danger-50 dark:bg-danger-900/10 border border-danger-200 dark:border-danger-800'
          }`}
        >
          <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">Your P&L</div>
          <div className={`font-semibold ${userPL.value >= 0 ? 'text-success-700 dark:text-success-400' : 'text-danger-700 dark:text-danger-400'}`}>
            {formatters.currency(userPL.value)} ({formatters.percentage(userPL.percentage)})
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-500 mt-1">
            {trade.quantity} shares @ {formatters.currency(trade.buyPrice)}
          </div>
        </motion.div>
      )}

      {/* Volume */}
      <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
        <Volume2 className="w-4 h-4" />
        <span>Vol: {formatters.compactNumber(data.volume)}</span>
      </div>

      {/* Last Updated */}
      <div className="mt-2 text-xs text-slate-500 dark:text-slate-500">
        Updated {formatters.time(data.timestamp)}
      </div>
    </Card>
  )
}