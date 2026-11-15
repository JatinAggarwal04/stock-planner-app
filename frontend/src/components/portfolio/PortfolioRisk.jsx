//frontend/src/components/portfolio/PortfolioRisk.jsx
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { stockService } from '../../services/stockService'
import { useWatchlistStore } from '../../context/WatchlistContext'
import { formatters } from '../../utils/formatters'
import Card from '../ui/Card'
import { ActionBadge, AlertList } from './PositionStatus'

const signedCurrency = (value) => `${value >= 0 ? '+' : ''}${formatters.currency(value)}`

function Stat({ label, value, tone }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</div>
      <div className={`text-lg font-bold ${tone || 'text-slate-900 dark:text-white'}`}>{value}</div>
    </div>
  )
}

// Dashboard overview of every held position: P&L, money at risk to stops, concentration and alerts
export default function PortfolioRisk() {
  const { trades } = useWatchlistStore()
  const navigate = useNavigate()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['portfolio-review', trades],
    queryFn: () => stockService.reviewHoldings(trades),
    refetchInterval: 60000,
    enabled: Object.keys(trades).length > 0,
  })

  if (!Object.keys(trades).length) return null
  if (isLoading) return <div className="h-40 skeleton rounded-xl mb-8" />
  if (isError || !data) return null

  const { summary, positions } = data
  return (
    <Card className="p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <ShieldAlert className="w-5 h-5" /> Portfolio Risk
        </h2>
        {summary.needs_attention > 0 && (
          <span className="text-sm font-medium text-amber-600 dark:text-amber-400">
            {summary.needs_attention} {summary.needs_attention === 1 ? 'position needs' : 'positions need'} attention
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <Stat label="Value" value={formatters.currency(summary.market_value)} />
        <Stat
          label="P&L"
          value={signedCurrency(summary.pnl)}
          tone={summary.pnl >= 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'}
        />
        {summary.past_stop_value > 0 ? (
          <Stat
            label="Past their stop"
            value={`${formatters.currency(summary.past_stop_value)} (${summary.past_stop_pct}%)`}
            tone="text-danger-600 dark:text-danger-400"
          />
        ) : (
          <Stat label="At risk to stops" value={`${formatters.currency(summary.risk_to_stops)} (${summary.risk_to_stops_pct}%)`} />
        )}
        <Stat label="Profit locked in" value={formatters.currency(summary.locked_in_profit)} />
      </div>

      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {positions.map((p) => (
          <button
            key={p.symbol}
            onClick={() => navigate(`/stock/${p.symbol}`)}
            className="w-full text-left py-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg px-2 -mx-2 transition-colors"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900 dark:text-white">{p.symbol.replace('.NS', '')}</span>
                <ActionBadge action={p.plan_action} />
                <span className="text-xs text-slate-500">{p.weight_pct}% of portfolio</span>
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-300">
                <span className={p.pnl >= 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'}>
                  {signedCurrency(p.pnl)} ({p.pnl_pct > 0 ? '+' : ''}{p.pnl_pct}%)
                </span>
                {' · '}stop {formatters.currency(p.exit_plan.stop)}
                {p.exit_plan.stop_type === 'trailing' && ' (trailing)'}
              </div>
            </div>
            {p.alerts.length > 0 && (
              <div className="mt-2">
                <AlertList alerts={p.alerts} />
              </div>
            )}
          </button>
        ))}
      </div>

      <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
        Stops use 2× the stock's normal daily move (ATR), capped at a 7% loss, and trail once you're 1 ATR in
        profit. HOLD / REVIEW / EXIT are risk rules, not predictions.
      </p>
    </Card>
  )
}
