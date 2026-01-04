//frontend/src/components/stock-detail/NewsPanel.jsx
import { ExternalLink, Newspaper } from 'lucide-react'
import { formatters } from '../../utils/formatters'
import Card from '../ui/Card'
import { motion } from 'framer-motion'

export default function NewsPanel({ news }) {
  if (!news || news.length === 0) {
    return (
      <Card className="p-6">
        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-4">
          Latest News
        </h3>
        <div className="text-center py-8 text-slate-500">
          <Newspaper className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No recent news available</p>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6">
      <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        <Newspaper className="w-5 h-5" />
        Latest News
      </h3>

      <div className="space-y-4">
        {news.map((article, index) => (
          <motion.a
            key={index}
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="block p-4 bg-slate-50 dark:bg-slate-800 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors group"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <h4 className="font-medium text-slate-900 dark:text-white mb-2 group-hover:text-primary-600 transition-colors line-clamp-2">
                  {article.title}
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {formatters.date(article.published)}
                </p>
              </div>
              <ExternalLink className="w-4 h-4 text-slate-400 group-hover:text-primary-600 flex-shrink-0" />
            </div>
          </motion.a>
        ))}
      </div>
    </Card>
  )
}