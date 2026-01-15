//frontend/src/components/stock-detail/TechnicalIndicators.jsx
import { Activity, TrendingUp, BarChart3 } from 'lucide-react'
import Card from '../ui/Card'
import Badge from '../ui/Badge'

export default function TechnicalIndicators({ data }) {
  // Check if we have the new "views" structure inside recommendation
  const views = data.recommendation?.views

  if (!views) return null

  const shortTerm = views.short_term
  const longTerm = views.long_term

  return (
    <Card className="p-6">
      <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-6">
        Technical Analysis Views
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Short Term View */}
        <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold text-slate-700 dark:text-slate-500 flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary-500" /> Short Term (Weeks)
            </h4>
            <Badge
              variant={shortTerm.signal === 'Bullish' ? 'success' : shortTerm.signal === 'Bearish' ? 'danger' : 'default'}
            >
              {shortTerm.signal}
            </Badge>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400">Confidence</span>
              <span className="font-medium dark:text-slate-200">{shortTerm.confidence}%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400">RSI (14)</span>
              <span className="font-medium dark:text-slate-200">{shortTerm.indicators.rsi}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400">MACD Diff</span>
              <span className={`font-medium ${shortTerm.indicators.macd_diff > 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'}`}>
                {shortTerm.indicators.macd_diff}
              </span>
            </div>

            <div className="pt-3 border-t border-slate-200 dark:border-slate-700">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">Key Drivers:</p>
              <div className="flex flex-wrap gap-2">
                {shortTerm.reasons.map((reason, i) => (
                  <span key={i} className="text-xs px-2.5 py-1 bg-indigo-50 dark:bg-indigo-500/20 rounded border border-indigo-100 dark:border-indigo-500/30 text-indigo-700 dark:text-indigo-300 font-medium">
                    {reason}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Long Term View */}
        <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary-500" /> Long Term (Months)
            </h4>
            <Badge
              variant={longTerm.signal === 'Bullish' ? 'success' : longTerm.signal === 'Bearish' ? 'danger' : 'default'}
            >
              {longTerm.signal}
            </Badge>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400">Confidence</span>
              <span className="font-medium dark:text-slate-200">{longTerm.confidence}%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400">200 SMA</span>
              <span className="font-medium dark:text-slate-200">{longTerm.indicators.sma_200}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500 dark:text-slate-400">ADX Strength</span>
              <span className="font-medium dark:text-slate-200">{longTerm.indicators.adx}</span>
            </div>

            <div className="pt-3 border-t border-slate-200 dark:border-slate-700">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">Key Drivers:</p>
              <div className="flex flex-wrap gap-2">
                {longTerm.reasons.map((reason, i) => (
                  <span key={i} className="text-xs px-2.5 py-1 bg-indigo-50 dark:bg-indigo-500/20 rounded border border-indigo-100 dark:border-indigo-500/30 text-indigo-700 dark:text-indigo-300 font-medium">
                    {reason}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}