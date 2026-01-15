//frontend/src/components/watchlist/WatchlistGrid.jsx
import { useQuery } from '@tanstack/react-query'
import { useWatchlistStore } from '../../context/WatchlistContext'
import { stockService } from '../../services/stockService'
import StockCard from './StockCard'
import { motion } from 'framer-motion'

export default function WatchlistGrid() {
  const { watchlist } = useWatchlistStore()

  const { data: quotes, isLoading } = useQuery({
    queryKey: ['watchlist-quotes', watchlist],
    queryFn: () => stockService.getBatchQuotes(watchlist),
    refetchInterval: 15000, // Update every 15 seconds for better performance
    enabled: watchlist.length > 0,
  })

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-48 skeleton rounded-xl"></div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {quotes?.map((quote, index) => (
        <motion.div
          key={quote.symbol}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
        >
          <StockCard data={quote} />
        </motion.div>
      ))}
    </div>
  )
}