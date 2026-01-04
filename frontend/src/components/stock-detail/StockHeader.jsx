//frontend/src/components/stock-detail/StockHeader.jsx
import { TrendingUp, TrendingDown, Star, Plus } from 'lucide-react'
import { useWatchlistStore } from '../../context/WatchlistContext'
import { formatters } from '../../utils/formatters'
import { SIGNAL_COLORS, RISK_COLORS } from '../../utils/constants'
import Card from '../ui/Card'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'

export default function StockHeader({ data }) {
  const { isInWatchlist, addToWatchlist, removeFromWatchlist } = useWatchlistStore()
  const inWatchlist = isInWatchlist(data.symbol)

  const signal = data.recommendation.signal
  const confidence = data.recommendation.confidence_score
  const isPositive = confidence >= 55

  const handleWatchlistToggle = () => {
    if (inWatchlist) {
      removeFromWatchlist(data.symbol)
      toast.success('Removed from watchlist')
    } else {
      addToWatchlist(data.symbol)
      toast.success('Added to watchlist')
    }
  }

  return (
    <Card className="p-6">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        {/* Left - Company Info */}
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white font-mono">
              {data.symbol.replace('.NS', '')}
            </h1>
            <Button
              variant="outline"
              size="sm"
              onClick={handleWatchlistToggle}
              className="p-2"
            >
              <Star
                className={`w-5 h-5 ${inWatchlist ? 'fill-yellow-400 text-yellow-400' : ''}`}
              />
            </Button>
          </div>
          <p className="text-lg text-slate-600 dark:text-slate-400 mb-4">
            {data.company_name}
          </p>

          {/* Price */}
          <div className="flex items-baseline gap-4 mb-4">
            <span className="text-4xl font-bold text-slate-900 dark:text-white">
              {formatters.currency(data.current_price)}
            </span>
            <div
              className={`flex items-center gap-2 text-xl font-semibold ${
                isPositive ? 'text-success-600' : 'text-danger-600'
              }`}
            >
              {isPositive ? (
                <TrendingUp className="w-6 h-6" />
              ) : (
                <TrendingDown className="w-6 h-6" />
              )}
            </div>
          </div>

          {/* Market Data */}
          <div className="flex flex-wrap gap-4 text-sm">
            <div>
              <span className="text-slate-500">52W High: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.market_data['52_week_high'])}
              </span>
            </div>
            <div>
              <span className="text-slate-500">52W Low: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.market_data['52_week_low'])}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Volume: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatters.compactNumber(data.market_data.current_volume)}
              </span>
            </div>
          </div>
        </div>

        {/* Right - Recommendation */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="sm:w-72 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 p-6 rounded-xl border-2"
          style={{ borderColor: SIGNAL_COLORS[signal] }}
        >
          <div className="text-center">
            <div className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">
              AI Recommendation
            </div>
            <div
              className="text-3xl font-bold mb-3"
              style={{ color: SIGNAL_COLORS[signal] }}
            >
              {signal.replace('_', ' ')}
            </div>

            {/* Confidence Bar */}
            <div className="mb-4">
              <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400 mb-2">
                <span>Confidence</span>
                <span className="font-semibold">{confidence.toFixed(1)}%</span>
              </div>
              <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${confidence}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                  className="h-full rounded-full"
                  style={{ backgroundColor: SIGNAL_COLORS[signal] }}
                />
              </div>
            </div>

            {/* Risk Rating */}
            <Badge
              variant={
                data.recommendation.risk_rating === 'Low'
                  ? 'success'
                  : data.recommendation.risk_rating === 'Medium'
                  ? 'warning'
                  : 'danger'
              }
            >
              {data.recommendation.risk_rating} Risk
            </Badge>

            {/* Model Info */}
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <div className="text-xs text-slate-500 dark:text-slate-500 space-y-1">
                <div>ML Accuracy: {data.ml_analysis.model_accuracy}%</div>
                <div>Sentiment: {data.sentiment_analysis.sentiment}</div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Personalized Alert if user has position */}
      {data.personalized_recommendation && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className={`mt-6 p-4 rounded-lg border-2 ${
            data.personalized_recommendation.position_summary.profit_loss >= 0
              ? 'bg-success-50 dark:bg-success-900/10 border-success-500'
              : 'bg-danger-50 dark:bg-danger-900/10 border-danger-500'
          }`}
        >
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <div className="font-semibold text-slate-900 dark:text-white mb-1">
                Your Position
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
                {data.personalized_recommendation.recommendation.message}
              </p>
              <div className="flex items-center gap-4 text-sm">
                <div>
                  <span className="text-slate-500">P&L: </span>
                  <span
                    className={`font-semibold ${
                      data.personalized_recommendation.position_summary.profit_loss >= 0
                        ? 'text-success-600'
                        : 'text-danger-600'
                    }`}
                  >
                    {formatters.currency(
                      data.personalized_recommendation.position_summary.profit_loss
                    )}{' '}
                    (
                    {formatters.percentage(
                      data.personalized_recommendation.position_summary.profit_loss_pct
                    )}
                    )
                  </span>
                </div>
              </div>
            </div>
            <Badge
              variant={
                data.personalized_recommendation.recommendation.action.includes('BUY')
                  ? 'success'
                  : data.personalized_recommendation.recommendation.action.includes('SELL')
                  ? 'danger'
                  : 'warning'
              }
            >
              {data.personalized_recommendation.recommendation.action.replace('_', ' ')}
            </Badge>
          </div>
        </motion.div>
      )}
    </Card>
  )
}
