//frontend/src/components/ui/Badge.jsx
export default function Badge({ children, variant = 'default', className = '' }) {
  const variants = {
    default: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:border dark:border-slate-700',
    success: 'bg-success-50 text-success-700 dark:bg-success-500/10 dark:text-success-400 dark:border dark:border-success-500/20',
    danger: 'bg-danger-50 text-danger-700 dark:bg-danger-500/10 dark:text-danger-400 dark:border dark:border-danger-500/20',
    warning: 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400 dark:border dark:border-amber-500/20',
    primary: 'bg-primary-50 text-primary-700 dark:bg-primary-500/10 dark:text-primary-400 dark:border dark:border-primary-500/20',
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  )
}