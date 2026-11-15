//frontend/src/components/portfolio/PositionStatus.jsx
import { AlertTriangle, Info, AlertOctagon } from 'lucide-react'
import Badge from '../ui/Badge'

const ACTION_VARIANT = { HOLD: 'success', REVIEW: 'warning', EXIT: 'danger' }
const ALERT_STYLE = {
  critical: { icon: AlertOctagon, className: 'text-danger-600 dark:text-danger-400' },
  warning: { icon: AlertTriangle, className: 'text-amber-600 dark:text-amber-400' },
  info: { icon: Info, className: 'text-slate-500 dark:text-slate-400' },
}

// HOLD / REVIEW / EXIT from the backend's exit rules (backend/positions.py): risk rules, not predictions
export function ActionBadge({ action }) {
  return <Badge variant={ACTION_VARIANT[action] || 'default'}>{action}</Badge>
}

export function AlertList({ alerts }) {
  if (!alerts?.length) return null
  return (
    <ul className="space-y-1.5">
      {alerts.map((alert) => {
        const { icon: Icon, className } = ALERT_STYLE[alert.level] || ALERT_STYLE.info
        return (
          <li key={alert.type} className={`flex items-start gap-2 text-sm ${className}`}>
            <Icon className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{alert.message}</span>
          </li>
        )
      })}
    </ul>
  )
}
