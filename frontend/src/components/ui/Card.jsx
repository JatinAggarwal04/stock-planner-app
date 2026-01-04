//frontend/src/components/ui/Card.jsx
import { motion } from 'framer-motion'

export default function Card({ children, className = '', hover = false, ...props }) {
  return (
    <motion.div
      className={`bg-white dark:bg-dark-surface rounded-xl border border-slate-200 dark:border-dark-border ${
        hover ? 'card-hover cursor-pointer' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  )
}