//frontend/src/components/stock-detail/PriceRanges.jsx
import { formatters } from '../../utils/formatters'
import Card from '../ui/Card'

const HORIZONS = [
  ['1_month', '1 month'],
  ['3_months', '3 months'],
  ['6_months', '6 months'],
  ['1_year', '1 year'],
]

// Symmetric volatility ranges instead of single "upside" targets: the price is about as likely to end near
// the low end as the high end (backend TradingPlanGenerator.calculate_long_term_targets)
export default function PriceRanges({ ranges, currentPrice }) {
  if (!ranges) return null

  return (
    <Card className="p-6">
      <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-1">Likely Price Ranges</h3>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
        Roughly two in three outcomes fall inside each range if volatility stays similar. Not targets.
      </p>

      <div className="space-y-3">
        {HORIZONS.filter(([key]) => ranges[key]).map(([key, label]) => {
          const { low, high } = ranges[key]
          const position = ((currentPrice - low) / (high - low)) * 100
          return (
            <div key={key}>
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-slate-700 dark:text-slate-300">{label}</span>
                <span className="text-slate-600 dark:text-slate-400">
                  {formatters.currency(low)} – {formatters.currency(high)}
                </span>
              </div>
              <div className="relative h-2 rounded-full bg-gradient-to-r from-danger-200 via-slate-200 to-success-200 dark:from-danger-500/30 dark:via-slate-700 dark:to-success-500/30">
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-1 h-4 bg-slate-900 dark:bg-white rounded"
                  style={{ left: `${position}%` }}
                  title={`Now ${formatters.currency(currentPrice)}`}
                />
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
