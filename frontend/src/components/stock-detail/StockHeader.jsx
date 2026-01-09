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

export default function StockHeader({ data, priceChange, timeRange }) {
  const { isInWatchlist, addToWatchlist, removeFromWatchlist } = useWatchlistStore()
  const inWatchlist = isInWatchlist(data.symbol)

  const signal = data.recommendation.signal
  const confidence = data.recommendation.confidence_score

  // Use dynamic price change if available, otherwise fallback (though we should always have it after chart load)
  const displayChange = priceChange ? priceChange.change : 0
  const displayPercent = priceChange ? priceChange.changePercent : 0
  const isPositive = displayPercent >= 0

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
          <div className="flex flex-wrap items-baseline gap-2 sm:gap-4 mb-4">
            <span className="text-4xl font-bold text-slate-900 dark:text-white">
              {formatters.currency(data.current_price)}
            </span>
            <div
              className={`flex items-center gap-1 sm:gap-2 text-lg sm:text-xl font-semibold ${isPositive ? 'text-success-600' : 'text-danger-600'
                }`}
            >
              {isPositive ? (
                <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6" />
              ) : (
                <TrendingDown className="w-5 h-5 sm:w-6 sm:h-6" />
              )}
              <span>
                {isPositive ? '+' : ''}{formatters.currency(Math.abs(displayChange))}
                <span className="ml-1">
                  ({isPositive ? '+' : ''}{displayPercent.toFixed(2)}%)
                </span>
                <span className="text-sm ml-1 text-slate-500 font-normal">({timeRange})</span>
              </span>
            </div>
          </div>

          {/* Market Data Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-2 gap-x-4 sm:gap-x-8 text-sm mt-4">
            <div>
              <span className="text-slate-500 dark:text-slate-400">Open: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.market_data.today_open)}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">High: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.market_data.today_high)}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Low: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.market_data.today_low)}
              </span>
            </div>

            <div>
              <span className="text-slate-500 dark:text-slate-400">52W High: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.market_data['52_week_high'])}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">52W Low: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.market_data['52_week_low'])}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Volume: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatters.compactNumber(data.market_data.current_volume)}
              </span>
            </div>

            <div>
              <span className="text-slate-500 dark:text-slate-400">Mkt Cap: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {formatters.compactNumber(data.market_data.market_cap)}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">P/E Ratio: </span>
              <span className="font-semibold text-slate-900 dark:text-white">
                {data.market_data.pe_ratio}
              </span>
            </div>
          </div>
        </div>

        {/* Right - Recommendation */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className={`sm:w-72 p-6 rounded-2xl border backdrop-blur-sm shadow-xl relative overflow-hidden transition-all duration-300 ${signal === 'BUY'
            ? 'bg-gradient-to-br from-white to-success-50 dark:from-slate-800 dark:to-slate-800 border-success-200 dark:border-success-500/50 shadow-success-200/50 dark:shadow-none'
            : signal === 'SELL'
              ? 'bg-gradient-to-br from-white to-danger-50 dark:from-slate-800 dark:to-slate-800 border-danger-200 dark:border-danger-500/50 shadow-danger-200/50 dark:shadow-none'
              : 'bg-gradient-to-br from-white to-slate-50 dark:from-slate-800 dark:to-slate-800 border-slate-200 dark:border-slate-700'
            }`}
        >
          <div className="text-center relative z-10">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
              Our Verdict
            </div>
            <div
              className="text-4xl font-extrabold mb-4 tracking-tight drop-shadow-sm"
              style={{ color: SIGNAL_COLORS[signal] }}
            >
              {signal.replace('_', ' ')}
            </div>

            {/* Confidence Bar */}
            <div className="mb-6">
              <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-300 mb-2 font-medium">
                <span>Signal Strength</span>
                <span className="font-bold">{confidence.toFixed(0)}%</span>
              </div>
              <div className="h-2.5 bg-slate-200/50 dark:bg-slate-700/50 rounded-full overflow-hidden backdrop-blur-sm">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${confidence}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                  className="h-full rounded-full shadow-lg"
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
              className="px-4 py-1.5 text-xs font-semibold uppercase tracking-wide shadow-sm"
            >
              Risk Level: {data.recommendation.risk_rating}
            </Badge>

            {/* Model Info */}
            <div className="mt-6 pt-4 border-t border-slate-200/60 dark:border-slate-700/60">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="text-slate-500 dark:text-slate-400">AI Confidence</div>
                <div className="font-semibold text-slate-900 dark:text-white text-right">
                  {typeof data.ml_analysis.model_accuracy === 'number'
                    ? Math.round(data.ml_analysis.model_accuracy) + '%'
                    : Math.round(confidence) + '%'}
                </div>

                <div className="text-slate-500 dark:text-slate-400">News Sentiment</div>
                <div className={`font-semibold text-right ${data.sentiment_analysis.sentiment === 'Bullish' ? 'text-success-600 dark:text-success-400' :
                  data.sentiment_analysis.sentiment === 'Bearish' ? 'text-danger-600 dark:text-danger-400' : 'text-slate-600 dark:text-slate-400'
                  }`}>
                  {
                    data.sentiment_analysis.sentiment === 'Bullish' ? 'Positive' :
                      data.sentiment_analysis.sentiment === 'Bearish' ? 'Negative' : 'Neutral'
                  }
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Personalized Alert if user has position */}
      {
        data.personalized_recommendation && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className={`mt-6 p-4 rounded-lg border-2 ${data.personalized_recommendation.position_summary.profit_loss >= 0
              ? 'bg-success-50 dark:bg-emerald-950/50 border-success-500 dark:border-success-500/50'
              : 'bg-danger-50 dark:bg-red-950/50 border-danger-500 dark:border-danger-500/50'
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
                      className={`font-semibold ${data.personalized_recommendation.position_summary.profit_loss >= 0
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
        )
      }
    </Card >
  )
}
