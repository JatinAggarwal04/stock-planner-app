import { X, TrendingUp } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function StockContextChip({ symbol, show, onToggle }) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: -10, height: 0 }}
          animate={{ opacity: 1, y: 0, height: 'auto' }}
          exit={{ opacity: 0, y: -10, height: 0 }}
          className="mb-3 overflow-hidden"
        >
          <div className="inline-flex items-center gap-2 px-3 py-2 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg">
            <TrendingUp className="w-4 h-4 text-primary-600" />
            <span className="text-sm font-medium text-primary-700 dark:text-primary-400">
              Context: {symbol.replace('.NS', '')}
            </span>
            <button
              onClick={onToggle}
              className="p-0.5 hover:bg-primary-100 dark:hover:bg-primary-900/30 rounded transition-colors"
            >
              <X className="w-3.5 h-3.5 text-primary-600" />
            </button>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-500 mt-2">
            I'll answer questions about this stock. Click X to switch to general mode.
          </p>
        </motion.div>
      )}
    </AnimatePresence>
  )
}