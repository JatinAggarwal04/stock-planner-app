//frontend/src/components/stock-detail/TradePanel.jsx
import { useState } from 'react'
import { DollarSign, Hash, TrendingUp, Target, Shield, Calendar, TrendingDown, Percent } from 'lucide-react'
import { formatters } from '../../utils/formatters'
import { useWatchlistStore } from '../../context/WatchlistContext'
import Card from '../ui/Card'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Badge from '../ui/Badge'
import Modal from '../ui/Modal'
import toast from 'react-hot-toast'
import { format } from 'date-fns'

export default function TradePanel({ data, symbol }) {
  const { getTrade, recordTrade, removeTrade } = useWatchlistStore()
  const existingTrade = getTrade(symbol)

  const [tradeType, setTradeType] = useState(existingTrade?.type || 'BUY')
  const [buyPrice, setBuyPrice] = useState(existingTrade?.buyPrice || '')
  const [quantity, setQuantity] = useState(existingTrade?.quantity || '')
  const [buyDate, setBuyDate] = useState(() => {
    if (existingTrade?.buyDate) {
      try {
        return format(new Date(existingTrade.buyDate), 'yyyy-MM-dd')
      } catch {
        return format(new Date(), 'yyyy-MM-dd')
      }
    }
    return format(new Date(), 'yyyy-MM-dd')
  })
  const [showForm, setShowForm] = useState(!existingTrade)
  const [showPartialModal, setShowPartialModal] = useState(false)
  const [partialType, setPartialType] = useState('PERCENTAGE') // PERCENTAGE or QUANTITY
  const [partialValue, setPartialValue] = useState('')

  const currentPrice = data.current_price

  // Calculate P&L
  const calculatePL = () => {
    if (!existingTrade) return null

    const invested = existingTrade.buyPrice * existingTrade.quantity
    const currentValue = currentPrice * existingTrade.quantity
    
    // For SHORT positions, profit is when price goes down
    const profitLoss = existingTrade.type === 'SELL' 
      ? invested - currentValue  // Short: profit when current < entry
      : currentValue - invested  // Long: profit when current > entry
      
    const profitLossPct = (profitLoss / invested) * 100

    let daysSinceEntry = 0
    try {
      if (existingTrade.buyDate) {
        daysSinceEntry = Math.floor(
          (new Date() - new Date(existingTrade.buyDate)) / (1000 * 60 * 60 * 24)
        )
      }
    } catch (error) {
      console.error('Error calculating days:', error)
      daysSinceEntry = 0
    }

    return {
      invested,
      currentValue,
      profitLoss,
      profitLossPct,
      daysSinceEntry,
    }
  }

  const pl = calculatePL()

  const handleSaveTrade = () => {
    if (!buyPrice || !quantity) {
      toast.error('Please fill all fields')
      return
    }

    const tradeData = {
      type: tradeType,
      buyPrice: parseFloat(buyPrice),
      quantity: parseInt(quantity),
      buyDate: new Date(buyDate).toISOString(),
      currentPrice: currentPrice,
    }

    recordTrade(symbol, tradeData)
    toast.success(`${tradeType === 'BUY' ? 'Long' : 'Short'} position recorded!`)
    setShowForm(false)
  }

  const handleSquareOff = (partial = false, sellQuantity = null) => {
    if (!existingTrade) return

    const pl = calculatePL()
    const qtyToSell = sellQuantity || existingTrade.quantity
    const partialPL = (pl.profitLoss / existingTrade.quantity) * qtyToSell
    const partialPct = (partialPL / (existingTrade.buyPrice * qtyToSell)) * 100

    if (partial && sellQuantity < existingTrade.quantity) {
      // Partial square off - update quantity
      const newQuantity = existingTrade.quantity - sellQuantity
      const tradeData = {
        ...existingTrade,
        quantity: newQuantity,
      }
      recordTrade(symbol, tradeData)
      
      const message = partialPL >= 0
        ? `Partial exit: ${sellQuantity} shares with profit of ${formatters.currency(partialPL)} (${formatters.percentage(partialPct)})`
        : `Partial exit: ${sellQuantity} shares with loss of ${formatters.currency(Math.abs(partialPL))} (${formatters.percentage(partialPct)})`
      
      toast.success(message)
      setShowPartialModal(false)
      setPartialValue('')
    } else {
      // Full square off - close position
      const message = pl.profitLoss >= 0
        ? `Position closed with profit of ${formatters.currency(pl.profitLoss)} (${formatters.percentage(pl.profitLossPct)})`
        : `Position closed with loss of ${formatters.currency(Math.abs(pl.profitLoss))} (${formatters.percentage(pl.profitLossPct)})`

      removeTrade(symbol)
      toast.success(message)
      setShowForm(true)
      setBuyPrice('')
      setQuantity('')
      setBuyDate(format(new Date(), 'yyyy-MM-dd'))
    }
  }

  const calculatePartialQuantity = () => {
    if (!partialValue || !existingTrade) return 0
    
    if (partialType === 'PERCENTAGE') {
      const pct = parseFloat(partialValue)
      return Math.floor((pct / 100) * existingTrade.quantity)
    } else {
      return parseInt(partialValue)
    }
  }

  const handlePartialSquareOff = () => {
    const qty = calculatePartialQuantity()
    
    if (qty <= 0 || qty >= existingTrade.quantity) {
      toast.error('Invalid quantity. Must be less than current position.')
      return
    }
    
    handleSquareOff(true, qty)
  }

  const handleRemoveTrade = () => {
    removeTrade(symbol)
    toast.success('Trade removed')
    setShowForm(true)
    setBuyPrice('')
    setQuantity('')
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-slate-900 dark:text-white">
          {existingTrade ? 'Your Position' : 'Record Trade'}
        </h3>
        {existingTrade && !showForm && (
          <Button variant="outline" size="sm" onClick={() => setShowForm(true)}>
            Edit
          </Button>
        )}
      </div>

      {showForm ? (
        <div className="space-y-4">
          {/* Trade Type Toggle */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Position Type
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setTradeType('BUY')}
                className={`py-3 px-4 rounded-lg font-medium transition-all ${
                  tradeType === 'BUY'
                    ? 'bg-success-600 text-white shadow-lg scale-105'
                    : 'bg-slate-100 dark:bg-dark-hover text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-dark-border'
                }`}
              >
                <TrendingUp className="w-5 h-5 mx-auto mb-1" />
                Long (Buy)
              </button>
              <button
                onClick={() => setTradeType('SELL')}
                className={`py-3 px-4 rounded-lg font-medium transition-all ${
                  tradeType === 'SELL'
                    ? 'bg-danger-600 text-white shadow-lg scale-105'
                    : 'bg-slate-100 dark:bg-dark-hover text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-dark-border'
                }`}
              >
                <TrendingDown className="w-5 h-5 mx-auto mb-1" />
                Short (Sell)
              </button>
            </div>
          </div>

          <Input
            type="number"
            label="Entry Price (₹)"
            icon={DollarSign}
            value={buyPrice}
            onChange={(e) => setBuyPrice(e.target.value)}
            placeholder="2450.50"
            step="0.01"
          />

          <Input
            type="number"
            label="Quantity"
            icon={Hash}
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="10"
          />

          <Input
            type="date"
            label="Entry Date"
            icon={Calendar}
            value={buyDate}
            onChange={(e) => setBuyDate(e.target.value)}
            max={format(new Date(), 'yyyy-MM-dd')}
          />

          <div className="flex gap-2">
            <Button onClick={handleSaveTrade} className="flex-1">
              {existingTrade ? 'Update Position' : 'Save Position'}
            </Button>
            {existingTrade && (
              <Button variant="danger" onClick={handleRemoveTrade}>
                Remove
              </Button>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Position Summary */}
          {existingTrade && pl && (
            <>
              {/* Trade Type Badge */}
              <div className="flex items-center justify-between">
                <Badge variant={existingTrade.type === 'BUY' ? 'success' : 'danger'} className="text-sm px-3 py-1">
                  {existingTrade.type === 'BUY' ? '📈 LONG' : '📉 SHORT'} Position
                </Badge>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  Held for {pl.daysSinceEntry} {pl.daysSinceEntry === 1 ? 'day' : 'days'}
                </span>
              </div>

              {/* P&L Card */}
              <div
                className={`p-5 rounded-xl border-2 ${
                  pl.profitLoss >= 0
                    ? 'bg-success-50 dark:bg-success-900/10 border-success-500'
                    : 'bg-danger-50 dark:bg-danger-900/10 border-danger-500'
                }`}
              >
                <div className="text-center mb-4">
                  <div className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">
                    Unrealized P&L
                  </div>
                  <div
                    className={`text-4xl font-bold mb-1 ${
                      pl.profitLoss >= 0
                        ? 'text-success-700 dark:text-success-400'
                        : 'text-danger-700 dark:text-danger-400'
                    }`}
                  >
                    {pl.profitLoss >= 0 ? '+' : ''}
                    {formatters.currency(pl.profitLoss)}
                  </div>
                  <div
                    className={`text-xl font-semibold ${
                      pl.profitLoss >= 0 ? 'text-success-600 dark:text-success-500' : 'text-danger-600 dark:text-danger-500'
                    }`}
                  >
                    {pl.profitLoss >= 0 ? '+' : ''}
                    {formatters.percentage(pl.profitLossPct)}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                  <div className="text-center">
                    <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">Invested</div>
                    <div className="font-semibold text-slate-900 dark:text-white">
                      {formatters.currency(pl.invested)}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">Current Value</div>
                    <div className="font-semibold text-slate-900 dark:text-white">
                      {formatters.currency(pl.currentValue)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Position Details */}
              <div className="p-4 bg-slate-50 dark:bg-dark-hover rounded-lg space-y-3 border border-slate-200 dark:border-dark-border">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Entry Price</span>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {formatters.currency(existingTrade.buyPrice)}
                  </span>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Current Price</span>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {formatters.currency(currentPrice)}
                  </span>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Quantity</span>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {existingTrade.quantity} shares
                  </span>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Entry Date</span>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {existingTrade.buyDate 
                      ? format(new Date(existingTrade.buyDate), 'dd MMM yyyy')
                      : 'N/A'
                    }
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-3">
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => setShowPartialModal(true)}
                >
                  <Percent className="w-4 h-4" />
                  Partial Exit
                </Button>
                
                <Button
                  variant={pl.profitLoss >= 0 ? 'success' : 'danger'}
                  className="w-full"
                  onClick={() => handleSquareOff(false)}
                >
                  {existingTrade.type === 'BUY' ? (
                    <>
                      <TrendingDown className="w-5 h-5" />
                      Square Off (Sell)
                    </>
                  ) : (
                    <>
                      <TrendingUp className="w-5 h-5" />
                      Square Off (Buy)
                    </>
                  )}
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Partial Exit Modal */}
      <Modal
        isOpen={showPartialModal}
        onClose={() => {
          setShowPartialModal(false)
          setPartialValue('')
        }}
        title="Partial Exit"
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Exit Type
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setPartialType('PERCENTAGE')}
                className={`py-2 px-4 rounded-lg font-medium transition-all ${
                  partialType === 'PERCENTAGE'
                    ? 'bg-primary-600 text-white'
                    : 'bg-slate-100 dark:bg-dark-hover text-slate-700 dark:text-slate-300'
                }`}
              >
                By Percentage
              </button>
              <button
                onClick={() => setPartialType('QUANTITY')}
                className={`py-2 px-4 rounded-lg font-medium transition-all ${
                  partialType === 'QUANTITY'
                    ? 'bg-primary-600 text-white'
                    : 'bg-slate-100 dark:bg-dark-hover text-slate-700 dark:text-slate-300'
                }`}
              >
                By Quantity
              </button>
            </div>
          </div>

          <Input
            type="number"
            label={partialType === 'PERCENTAGE' ? 'Percentage to Exit (%)' : 'Quantity to Exit'}
            value={partialValue}
            onChange={(e) => setPartialValue(e.target.value)}
            placeholder={partialType === 'PERCENTAGE' ? '50' : '5'}
            step={partialType === 'PERCENTAGE' ? '1' : '1'}
          />

          {partialValue && existingTrade && (
            <div className="p-3 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-200 dark:border-blue-800">
              <div className="text-sm text-blue-900 dark:text-blue-300">
                <strong>Exit Quantity:</strong> {calculatePartialQuantity()} shares
                <br />
                <strong>Remaining:</strong> {existingTrade.quantity - calculatePartialQuantity()} shares
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setShowPartialModal(false)
                setPartialValue('')
              }}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handlePartialSquareOff}
              disabled={!partialValue || calculatePartialQuantity() <= 0}
              className="flex-1"
            >
              Confirm Exit
            </Button>
          </div>
        </div>
      </Modal>

      {/* AI Recommended Setup */}
      <div className="mt-6 pt-6 border-t border-slate-200 dark:border-dark-border">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
          AI Recommended Setup
        </h4>

        <div className="space-y-3">
          <div className="flex items-center gap-3 p-3 bg-primary-50 dark:bg-primary-500/10 rounded-lg border border-primary-200 dark:border-primary-400/30">
            <div className="w-8 h-8 bg-primary-100 dark:bg-primary-500/20 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-primary-700 dark:text-primary-400" />
            </div>
            <div className="flex-1">
              <div className="text-xs text-slate-700 dark:text-slate-200">Entry</div>
              <div className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.trade_setup.entry_price)}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 bg-danger-50 dark:bg-danger-500/10 rounded-lg border border-danger-200 dark:border-danger-400/30">
            <div className="w-8 h-8 bg-danger-100 dark:bg-danger-500/20 rounded-lg flex items-center justify-center">
              <Shield className="w-4 h-4 text-danger-600 dark:text-danger-400" />
            </div>
            <div className="flex-1">
              <div className="text-xs text-slate-700 dark:text-slate-200">Stop Loss</div>
              <div className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.trade_setup.stop_loss)}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 bg-success-50 dark:bg-success-500/10 rounded-lg border border-success-200 dark:border-success-400/30">
            <div className="w-8 h-8 bg-success-100 dark:bg-success-500/20 rounded-lg flex items-center justify-center">
              <Target className="w-4 h-4 text-success-600 dark:text-success-400" />
            </div>
            <div className="flex-1">
              <div className="text-xs text-slate-700 dark:text-slate-200">Targets</div>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="success" className="text-xs">
                  T1: {formatters.currency(data.trade_setup.targets.target_1)}
                </Badge>
                <Badge variant="success" className="text-xs">
                  T2: {formatters.currency(data.trade_setup.targets.target_2)}
                </Badge>
                <Badge variant="success" className="text-xs">
                  T3: {formatters.currency(data.trade_setup.targets.target_3)}
                </Badge>
              </div>
            </div>
          </div>

          <div className="text-center text-sm text-slate-600 dark:text-slate-300 pt-2">
            Risk:Reward = {data.trade_setup.risk_reward}
          </div>
        </div>
      </div>

      {/* Position Sizing */}
      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-900">
        <div className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-2">
          Recommended Position Size (2% risk)
        </div>
        <div className="text-xs text-blue-800 dark:text-blue-300 space-y-1">
          <div>Shares: {data.position_sizing.shares}</div>
          <div>Value: {formatters.currency(data.position_sizing.position_value)}</div>
          <div>Risk: {formatters.currency(data.position_sizing.risk_amount)}</div>
        </div>
      </div>
    </Card>
  )
}