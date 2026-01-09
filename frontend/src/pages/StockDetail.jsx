//frontend/src/pages/StockDetail.jsx
import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, MessageCircle } from 'lucide-react'
import { stockService } from '../services/stockService'
import { useWatchlistStore } from '../context/WatchlistContext'
import StockHeader from '../components/stock-detail/StockHeader'
import ChartView from '../components/stock-detail/ChartView'
import TechnicalIndicators from '../components/stock-detail/TechnicalIndicators'
import SupportResistance from '../components/stock-detail/SupportResistance'
import NewsPanel from '../components/stock-detail/NewsPanel'
import TradePanel from '../components/stock-detail/TradePanel'
import ChatInterface from '../components/chatbot/ChatInterface'
import Button from '../components/ui/Button'

export default function StockDetail() {
  const { symbol } = useParams()
  const navigate = useNavigate()
  const [showChat, setShowChat] = useState(false)

  const { getTrade } = useWatchlistStore()
  const trade = getTrade(symbol)

  // State for chart interaction
  const [timeRange, setTimeRange] = useState('1D')
  const [priceChange, setPriceChange] = useState(null)

  // Fetch full stock analysis
  const { data: analysis, isLoading, error } = useQuery({
    queryKey: ['stock-analysis', symbol, trade],
    queryFn: () => {
      if (trade) {
        return stockService.getPersonalizedAnalysis(
          symbol,
          trade.buyPrice,
          trade.quantity
        )
      }
      return stockService.analyzeStock(symbol)
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Callback to update price change from ChartView
  const handlePriceChange = useCallback((changeData) => {
    setPriceChange(changeData)
  }, [])

  // Chat context state
  const [chatContext, setChatContext] = useState(null)

  const handleAskAI = () => {
    if (!analysis) return

    // Prepare robust context for the AI
    const context = {
      type: 'stock',
      symbol: analysis.symbol,
      current_price: analysis.current_price,
      signal: analysis.recommendation?.signal || 'Neutral',
      has_position: !!trade,
      buy_price: trade?.averagePrice || 0,
      quantity: trade?.quantity || 0,
      // Pass the trading plan calculated by the backend (Handle both base and personalized Structure)
      trading_plan: analysis.personalized_recommendation?.trading_plan || analysis.trading_plan || null,
      personalized_recommendation: analysis.personalized_recommendation || null,
      trade_setup: analysis.trade_setup || null // Pass base trade setup too
    }

    setChatContext(context)
    setShowChat(true)
  }

  // Open generic chat
  const handleOpenChat = () => {
    setChatContext({
      type: 'stock',
      symbol: symbol,
      current_price: analysis?.current_price || 0,
      signal: analysis?.recommendation?.signal || 'Neutral'
    })
    setShowChat(true)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-dark-bg">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="space-y-6">
            <div className="h-32 skeleton rounded-xl"></div>
            <div className="h-96 skeleton rounded-xl"></div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="h-64 skeleton rounded-xl"></div>
              <div className="h-64 skeleton rounded-xl"></div>
              <div className="h-64 skeleton rounded-xl"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-dark-bg flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
            Error Loading Stock
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mb-6">
            {error.message || 'Failed to fetch stock data'}
          </p>
          <Button onClick={() => navigate('/dashboard')}>
            <ArrowLeft className="w-5 h-5" />
            Back to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-dark-bg overflow-x-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Back Button */}
        <Button
          variant="outline"
          onClick={() => navigate('/dashboard')}
          className="mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Watchlist
        </Button>

        {/* Stock Header */}
        <StockHeader
          data={analysis}
          priceChange={priceChange}
          timeRange={timeRange}
        />

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Left Column - Chart & Technical */}
          <div className="lg:col-span-2 space-y-6">
            <ChartView
              symbol={symbol}
              timeRange={timeRange}
              onTimeRangeChange={setTimeRange}
              onPriceChange={handlePriceChange}
              currentPrice={analysis.current_price}
            />
            <TechnicalIndicators data={analysis} />
            <SupportResistance data={analysis.support_resistance} />
          </div>

          {/* Right Column - Trade Panel & News */}
          <div className="space-y-6">
            <TradePanel
              data={analysis}
              symbol={symbol}
              onAskAI={handleAskAI}
            />
            <NewsPanel news={analysis.latest_news} />
          </div>
        </div>

        {/* AI Chat Button (Floating) */}
        <button
          onClick={handleOpenChat}
          className="fixed bottom-6 right-6 w-14 h-14 bg-primary-600 hover:bg-primary-700 text-white rounded-full shadow-lg flex items-center justify-center transition-all hover:scale-110 z-40"
        >
          <MessageCircle className="w-6 h-6" />
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-success-500 rounded-full animate-pulse"></span>
        </button>
      </div>

      {/* Chat Interface */}
      {showChat && (
        <ChatInterface
          onClose={() => setShowChat(false)}
          context={chatContext || { type: 'stock', symbol, current_price: analysis?.current_price }}
        />
      )}
    </div>
  )
}