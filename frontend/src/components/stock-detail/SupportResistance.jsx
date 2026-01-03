import { TrendingUp, TrendingDown, Target } from 'lucide-react'
import { formatters } from '../../utils/formatters'
import Card from '../ui/Card'
import Badge from '../ui/Badge'
import { motion } from 'framer-motion'

export default function SupportResistance({ data }) {
  const hasResistance = data.nearest_resistance !== null && data.nearest_resistance !== undefined
  const hasSupport = data.nearest_support !== null && data.nearest_support !== undefined

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-slate-900 dark:text-white">
          Support & Resistance
        </h3>
        <Badge
          variant={
            data.trend === 'Bullish'
              ? 'success'
              : data.trend === 'Bearish'
              ? 'danger'
              : 'default'
          }
        >
          {data.trend} Trend
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Resistance */}
        <div className="p-4 bg-danger-50 dark:bg-danger-950/20 rounded-xl border-2 border-danger-200 dark:border-danger-900">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-danger-100 dark:bg-danger-900/30 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-danger-600 dark:text-danger-400" />
            </div>
            <div>
              <div className="text-sm font-medium text-danger-900 dark:text-danger-200">
                Nearest Resistance
              </div>
              <div className="text-2xl font-bold text-slate-900 dark:text-white">
                {hasResistance
                  ? formatters.currency(data.nearest_resistance)
                  : 'N/A'}
              </div>
            </div>
          </div>

          {hasResistance && (
            <>
              <div className="flex items-center justify-between text-sm mb-3">
                <span className="text-slate-700 dark:text-slate-200">Distance</span>
                <span className="font-semibold text-danger-700 dark:text-danger-300">
                  +{data.resistance_distance_pct}%
                </span>
              </div>

              {/* Breakout Probability */}
              <div>
                <div className="flex items-center justify-between text-xs text-slate-700 dark:text-slate-200 mb-2">
                  <span>Breakout Probability</span>
                  <span className="font-semibold">
                    {data.resistance_breakout_probability.toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${data.resistance_breakout_probability}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                    className="h-full bg-danger-500 rounded-full"
                  />
                </div>
              </div>

              {/* All Resistance Levels */}
              {data.all_resistance_levels.length > 0 && (
                <div className="mt-4 pt-4 border-t border-danger-200 dark:border-danger-900">
                  <div className="text-xs text-slate-600 dark:text-slate-300 mb-2">All Levels</div>
                  <div className="flex flex-wrap gap-2">
                    {data.all_resistance_levels.slice(0, 3).map((level, idx) => (
                      <Badge key={idx} variant="danger" className="text-xs">
                        {formatters.currency(level)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {!hasResistance && (
            <p className="text-sm text-slate-700 dark:text-slate-200 mt-2">
              No clear resistance level detected in recent data. Price may be in discovery mode.
            </p>
          )}
        </div>

        {/* Support */}
        <div className="p-4 bg-success-50 dark:bg-success-950/20 rounded-xl border-2 border-success-200 dark:border-success-900">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-success-100 dark:bg-success-900/30 rounded-lg flex items-center justify-center">
              <TrendingDown className="w-5 h-5 text-success-600 dark:text-success-400" />
            </div>
            <div>
              <div className="text-sm font-medium text-success-900 dark:text-success-200">
                Nearest Support
              </div>
              <div className="text-2xl font-bold text-slate-900 dark:text-white">
                {hasSupport
                  ? formatters.currency(data.nearest_support)
                  : 'N/A'}
              </div>
            </div>
          </div>

          {hasSupport && (
            <>
              <div className="flex items-center justify-between text-sm mb-3">
                <span className="text-slate-700 dark:text-slate-200">Distance</span>
                <span className="font-semibold text-success-700 dark:text-success-300">
                  -{data.support_distance_pct}%
                </span>
              </div>

              {/* Breakdown Probability */}
              <div>
                <div className="flex items-center justify-between text-xs text-slate-700 dark:text-slate-200 mb-2">
                  <span>Breakdown Risk</span>
                  <span className="font-semibold">
                    {data.support_breakdown_probability.toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${data.support_breakdown_probability}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                    className="h-full bg-success-500 rounded-full"
                  />
                </div>
              </div>

              {/* All Support Levels */}
              {data.all_support_levels.length > 0 && (
                <div className="mt-4 pt-4 border-t border-success-200 dark:border-success-900">
                  <div className="text-xs text-slate-600 dark:text-slate-300 mb-2">All Levels</div>
                  <div className="flex flex-wrap gap-2">
                    {data.all_support_levels.slice(0, 3).map((level, idx) => (
                      <Badge key={idx} variant="success" className="text-xs">
                        {formatters.currency(level)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {!hasSupport && (
            <p className="text-sm text-slate-700 dark:text-slate-200 mt-2">
              No clear support level detected in recent data. Monitor closely for price consolidation.
            </p>
          )}
        </div>
      </div>

      {/* Current Price Indicator */}
      <div className="mt-6 flex items-center justify-center gap-2 text-sm">
        <Target className="w-4 h-4 text-primary-600" />
        <span className="text-slate-600 dark:text-slate-400">Current Price:</span>
        <span className="font-semibold text-slate-900 dark:text-white">
          {formatters.currency(data.current_price)}
        </span>
      </div>
    </Card>
  )
}
