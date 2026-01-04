//frontend/src/pages/Dashboard.jsx
import { useState } from 'react'
import { Plus, MessageCircle } from 'lucide-react'
import WatchlistGrid from '../components/watchlist/WatchlistGrid'
import AddStockModal from '../components/watchlist/AddStockModal'
import ChatInterface from '../components/chatbot/ChatInterface'
import { useWatchlistStore } from '../context/WatchlistContext'
import Button from '../components/ui/Button'
import { motion } from 'framer-motion'

export default function Dashboard() {
  const [showAddModal, setShowAddModal] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const { watchlist } = useWatchlistStore()

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-dark-bg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">
              My Watchlist
            </h1>
            <p className="text-slate-600 dark:text-slate-400">
              {watchlist.length} {watchlist.length === 1 ? 'stock' : 'stocks'} tracked
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={() => setShowChat(true)}
              className="relative"
            >
              <MessageCircle className="w-5 h-5" />
              <span className="hidden sm:inline">AI Assistant</span>
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-success-500 rounded-full animate-pulse"></span>
            </Button>

            <Button onClick={() => setShowAddModal(true)}>
              <Plus className="w-5 h-5" />
              <span className="hidden sm:inline">Add Stock</span>
            </Button>
          </div>
        </div>

        {/* Watchlist Grid */}
        {watchlist.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <div className="w-24 h-24 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-6">
              <Plus className="w-12 h-12 text-slate-400" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
              Your watchlist is empty
            </h3>
            <p className="text-slate-600 dark:text-slate-400 mb-6">
              Add stocks to start tracking their performance
            </p>
            <Button onClick={() => setShowAddModal(true)}>
              <Plus className="w-5 h-5" />
              Add Your First Stock
            </Button>
          </motion.div>
        ) : (
          <WatchlistGrid />
        )}
      </div>

      {/* Modals */}
      <AddStockModal isOpen={showAddModal} onClose={() => setShowAddModal(false)} />
      
      {showChat && (
        <ChatInterface 
          onClose={() => setShowChat(false)}
          context="general"
        />
      )}
    </div>
  )
}