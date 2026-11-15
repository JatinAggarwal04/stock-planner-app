//frontend/src/components/stock-detail/ExitPlan.jsx
import { useQuery } from '@tanstack/react-query'
import { stockService } from '../../services/stockService'
import { formatters } from '../../utils/formatters'
import { ActionBadge, AlertList } from '../portfolio/PositionStatus'

// Exit plan for the position held in this stock (same rules as the dashboard's Portfolio Risk card)
export default function ExitPlan({ symbol, trade }) {
  const { data } = useQuery({
    queryKey: ['position-review', symbol, trade],
    queryFn: () => stockService.reviewHoldings({ [symbol]: trade }),
    refetchInterval: 60000,
  })
  const review = data?.positions?.[0]
  if (!review) return null
  const plan = review.exit_plan

  return (
    <div className="p-4 border-t border-slate-100 dark:border-slate-800 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Exit plan</span>
        <ActionBadge action={review.plan_action} />
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">{review.plan_reason}</p>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-xs text-slate-500">{plan.stop_type === 'trailing' ? 'Trailing stop' : 'Stop-loss'}</div>
          <div className="font-semibold text-slate-900 dark:text-white">{formatters.currency(plan.stop)}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500">{plan.locked_in_profit > 0 ? 'Profit locked in' : 'At risk if stopped'}</div>
          <div className="font-semibold text-slate-900 dark:text-white">
            {formatters.currency(plan.locked_in_profit > 0 ? plan.locked_in_profit : plan.risk_to_stop)}
          </div>
        </div>
      </div>
      <AlertList alerts={review.alerts} />
    </div>
  )
}
