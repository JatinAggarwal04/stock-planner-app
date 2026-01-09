//frontend/src/components/stock-detail/TradePanel.jsx
import { useState, useEffect } from 'react'
import { DollarSign, Hash, TrendingUp, Target, Shield, Calendar, TrendingDown, Percent, Plus, Sparkles } from 'lucide-react'
import { formatters } from '../../utils/formatters'
import { useWatchlistStore } from '../../context/WatchlistContext'
import Card from '../ui/Card'
import Button from '../ui/Button'
import Badge from '../ui/Badge'
import toast from 'react-hot-toast'
import OrderPad from './OrderPad'

export default function TradePanel({ data, symbol, onAskAI }) {
  const { getTrade, recordTrade, getHistory, fetchTransactions, removeTrade } = useWatchlistStore()
  const portfolioItem = getTrade(symbol)
  const tradeHistory = getHistory(symbol)

  // Order Pad State
  const [showOrderPad, setShowOrderPad] = useState(false)
  const [orderType, setOrderType] = useState('BUY')
  const [loading, setLoading] = useState(false)

  // Fetch history on mount
  useEffect(() => {
    fetchTransactions(symbol)
  }, [symbol])

  const currentPrice = data.current_price

  // Calculate P&L for Portfolio Item
  const calculatePL = () => {
    if (!portfolioItem || portfolioItem.quantity === 0) return null

    const isLong = portfolioItem.quantity > 0
    const qty = Math.abs(portfolioItem.quantity)
    const avg = portfolioItem.averagePrice

    // Profit = (Current - Avg) * Qty (for Long)
    // Profit = (Avg - Current) * Qty (for Short)
    const profitLoss = isLong
      ? (currentPrice - avg) * qty
      : (avg - currentPrice) * qty

    const invested = avg * qty
    const profitLossPct = (profitLoss / invested) * 100

    return {
      invested,
      currentValue: currentPrice * qty,
      profitLoss,
      profitLossPct,
      isLong
    }
  }

  const pl = calculatePL()

  const handleOrderSubmit = async (tradeData) => {
    setLoading(true)
    try {
      await recordTrade(symbol, tradeData)
      toast.success('Trade Executed Successfully!')
      setShowOrderPad(false)
    } catch (error) {
      toast.error('Failed to execute trade')
    } finally {
      setLoading(false)
    }
  }

  const openOrderPad = (type) => {
    setOrderType(type)
    setShowOrderPad(true)
  }

  return (
    <div className="space-y-6">
      <OrderPad
        isOpen={showOrderPad}
        onClose={() => setShowOrderPad(false)}
        symbol={symbol}
        currentPrice={currentPrice}
        onSubmit={handleOrderSubmit}
        initialType={orderType}
        loading={loading}
      />

      {/* 1. Current Position Card */}
      {portfolioItem && Math.abs(portfolioItem.quantity) > 0 ? (
        <Card className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <div className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">Your Position</div>
              <div className={`text-2xl font-bold ${pl.isLong ? 'text-success-500' : 'text-danger-500'}`}>
                {pl.isLong ? 'LONG' : 'SHORT'} {Math.abs(portfolioItem.quantity)} Qty
              </div>
              <div className="text-sm text-slate-500 dark:text-slate-400">
                Avg. Price: {formatters.currency(portfolioItem.averagePrice)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium text-slate-500 dark:text-slate-400">Profit/Loss</div>
              <div className={`text-xl font-bold ${pl.profitLoss >= 0 ? 'text-success-500' : 'text-danger-500'}`}>
                {pl.profitLoss >= 0 ? '+' : ''}{formatters.currency(pl.profitLoss)}
                <span className="text-sm ml-1">({pl.profitLossPct.toFixed(2)}%)</span>
              </div>

              {/* AI Insight Button */}
              <div className="mt-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-2 border-primary-200 text-primary-600 hover:bg-primary-50 dark:border-primary-900/50 dark:text-primary-400 dark:hover:bg-primary-900/20 w-full justify-center"
                  onClick={() => onAskAI && onAskAI()}
                >
                  <Sparkles className="w-4 h-4" />
                  <span className="hidden sm:inline">Get AI Insight</span>
                  <span className="sm:hidden">Ask AI</span>
                </Button>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-4">
            <Button
              className="w-full"
              variant="success"
              onClick={() => openOrderPad('BUY')}
            >
              Add / Buy
            </Button>
            <Button
              className="w-full"
              variant="danger"
              onClick={() => openOrderPad('SELL')}
            >
              Reduce / Sell
            </Button>
          </div>
        </Card>
      ) : (
        /* Empty State - Start Trade */
        <Card className="p-8 text-center border-dashed border-2 border-slate-200 dark:border-slate-700 bg-transparent shadow-none">
          <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-full flex items-center justify-center mx-auto mb-4">
            <Plus className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-semibold mb-2 text-slate-900 dark:text-white">Start Trading {symbol}</h3>
          <p className="text-slate-500 dark:text-slate-400 mb-6 max-w-xs mx-auto">
            Track your P&L seamlessly by recording your trades here.
          </p>

          <div className="mb-6 flex justify-center">
            <Button
              variant="outline"
              size="sm"
              className="flex items-center gap-2 border-primary-200 text-primary-600 hover:bg-primary-50 dark:border-primary-900/50 dark:text-primary-400 dark:hover:bg-primary-900/20"
              onClick={() => onAskAI && onAskAI()}
            >
              <Sparkles className="w-4 h-4" />
              <span>Get AI Analysis</span>
            </Button>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button size="lg" variant="success" onClick={() => openOrderPad('BUY')}>
              Buy Shares
            </Button>
            <Button size="lg" variant="danger" onClick={() => openOrderPad('SELL')}>
              Short Sell
            </Button>
          </div>
        </Card>
      )}


      {/* 2. Trade History */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4 text-slate-900 dark:text-white">Recent Activity</h3>
        {tradeHistory && tradeHistory.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-500 dark:text-slate-400 uppercase bg-slate-50 dark:bg-slate-800/50">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3 text-right">Qty</th>
                  <th className="px-4 py-3 text-right">Price</th>
                  <th className="px-4 py-3 text-right">P&L</th>
                </tr>
              </thead>
              <tbody>
                {tradeHistory.map((trade) => (
                  <tr key={trade.id} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{formatters.date(trade.trade_date)}</td>
                    <td className="px-4 py-3">
                      <Badge variant={trade.type === 'BUY' ? 'success' : 'danger'}>
                        {trade.type}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right text-slate-700 dark:text-slate-300">{trade.quantity}</td>
                    <td className="px-4 py-3 text-right text-slate-700 dark:text-slate-300">{formatters.currency(trade.price)}</td>
                    <td className={`px-4 py-3 text-right font-medium ${trade.realized_pl > 0 ? 'text-success-600' : trade.realized_pl < 0 ? 'text-danger-600' : 'text-slate-400'
                      }`}>
                      {trade.realized_pl ? formatters.currency(trade.realized_pl) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-slate-500 dark:text-slate-400 py-4">No active trade records found.</div>
        )}
      </Card>

      {/* Sticky Mobile Footer */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 sm:hidden z-40 flex gap-4 pb-8 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]">
        <Button
          className="flex-1 text-lg font-bold py-6 shadow-lg shadow-success-500/20"
          variant="success"
          onClick={() => openOrderPad('BUY')}
        >
          BUY
        </Button>
        <Button
          className="flex-1 text-lg font-bold py-6 shadow-lg shadow-danger-500/20"
          variant="danger"
          onClick={() => openOrderPad('SELL')}
        >
          SELL
        </Button>
      </div>

    </div >
  )
}