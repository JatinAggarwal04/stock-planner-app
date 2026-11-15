//frontend/src/components/stock-detail/ResultsDrift.jsx
import { CalendarClock } from 'lucide-react'
import Card from '../ui/Card'
import Badge from '../ui/Badge'

const GROUPS = {
  strong_positive: { label: 'Strong positive reaction', variant: 'success' },
  neutral: { label: 'Muted reaction', variant: 'default' },
  strong_negative: { label: 'Strong negative reaction', variant: 'danger' },
}

const signed = (value) => `${value > 0 ? '+' : ''}${value.toFixed(2)}%`

// Shown for 60 trading days after quarterly results: how the market reacted, and how stocks with a
// similar reaction have done against the Nifty afterwards (see backend scripts/events.py)
export default function ResultsDrift({ data }) {
  if (!data) return null
  const group = GROUPS[data.group] || GROUPS.neutral
  const history = data.historical

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <CalendarClock className="w-5 h-5" />
          Results Reaction
        </h3>
        <Badge variant={group.variant}>{group.label}</Badge>
      </div>

      <p className="text-sm text-slate-600 dark:text-slate-300">
        Quarterly results on {data.results_date}: the stock moved{' '}
        <span className="font-semibold">{signed(data.reaction_vs_nifty_pct)}</span> vs the Nifty around the
        announcement, and <span className="font-semibold">{signed(data.since_reaction_vs_nifty_pct)}</span> since
        ({data.trading_days_since} trading days).
      </p>

      {history && (
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
          Historically, after a reaction like this, Nifty 50 stocks beat the Nifty over the next 60 trading
          days <span className="font-semibold">{history[data.group].beat_nifty_pct}%</span> of the time
          (strong positive reactions: {history.strong_positive.beat_nifty_pct}%, strong negative:{' '}
          {history.strong_negative.beat_nifty_pct}%). {data.days_remaining} days of that window are left.
        </p>
      )}

      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
        Based on 2,231 results of current Nifty 50 companies since 2015. A tendency across many stocks, not a
        prediction for this one.
      </p>
    </Card>
  )
}
