//frontend/src/components/ui/Badge.jsx
export default function Badge({ children, variant = 'default', className = '' }) {
  const variants = {
    default: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    success: 'bg-success-50 text-success-700 dark:bg-success-900/20 dark:text-success-400',
    danger: 'bg-danger-50 text-danger-700 dark:bg-danger-900/20 dark:text-danger-400',
    warning: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400',
    primary: 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400',
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  )
}