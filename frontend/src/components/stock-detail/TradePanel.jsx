import { useState } from 'react'
import { DollarSign, Hash, TrendingUp, Target, Shield } from 'lucide-react'
import { formatters } from '../../utils/formatters'
import { useWatchlistStore } from '../../context/WatchlistContext'
import Card from '../ui/Card'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Badge from '../ui/Badge'
import toast from 'react-hot-toast'

export default function TradePanel({ data, symbol }) {
  const { getTrade, recordTrade, removeTrade } = useWatchlistStore()
  const existingTrade = getTrade(symbol)

  const [buyPrice, setBuyPrice] = useState(existingTrade?.buyPrice || '')
  const [quantity, setQuantity] = useState(existingTrade?.quantity || '')
  const [showForm, setShowForm] = useState(!existingTrade)

  const handleSaveTrade = () => {
    if (!buyPrice || !quantity) {
      toast.error('Please fill all fields')
      return
    }

    recordTrade(symbol, {
      buyPrice: parseFloat(buyPrice),
      quantity: parseInt(quantity),
      date: new Date().toISOString(),
    })

    toast.success('Trade recorded successfully!')
    setShowForm(false)
    window.location.reload() // Reload to fetch personalized analysis
  }

  const handleRemoveTrade = () => {
    removeTrade(symbol)
    toast.success('Trade removed')
    setShowForm(true)
    setBuyPrice('')
    setQuantity('')
    window.location.reload()
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
          <Input
            type="number"
            label="Buy Price (₹)"
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

          <div className="flex gap-2">
            <Button onClick={handleSaveTrade} className="flex-1">
              {existingTrade ? 'Update Trade' : 'Save Trade'}
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
          {data.personalized_recommendation && (
            <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  Buy Price
                </span>
                <span className="font-semibold text-slate-900 dark:text-white">
                  {formatters.currency(existingTrade.buyPrice)}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  Quantity
                </span>
                <span className="font-semibold text-slate-900 dark:text-white">
                  {existingTrade.quantity} shares
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  Investment
                </span>
                <span className="font-semibold text-slate-900 dark:text-white">
                  {formatters.currency(
                    data.personalized_recommendation.position_summary.total_investment
                  )}
                </span>
              </div>

              <div className="pt-3 border-t border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
                    Current Value
                  </span>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {formatters.currency(
                      data.personalized_recommendation.position_summary.current_value
                    )}
                  </span>
                </div>
              </div>

              <div className="pt-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
                    P&L
                  </span>
                  <div className="text-right">
                    <div
                      className={`font-bold ${
                        data.personalized_recommendation.position_summary.profit_loss >= 0
                          ? 'text-success-600'
                          : 'text-danger-600'
                      }`}
                    >
                      {formatters.currency(
                        data.personalized_recommendation.position_summary.profit_loss
                      )}
                    </div>
                    <div
                      className={`text-sm ${
                        data.personalized_recommendation.position_summary.profit_loss >= 0
                          ? 'text-success-600'
                          : 'text-danger-600'
                      }`}
                    >
                      {formatters.percentage(
                        data.personalized_recommendation.position_summary.profit_loss_pct
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Trade Setup from ML */}
      <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4">
          Recommended Setup
        </h4>

        <div className="space-y-3">
          <div className="flex items-center gap-3 p-3 bg-primary-50 dark:bg-primary-900/10 rounded-lg">
            <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900/20 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-primary-600" />
            </div>
            <div className="flex-1">
              <div className="text-xs text-slate-600 dark:text-slate-400">Entry</div>
              <div className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.trade_setup.entry_price)}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 bg-danger-50 dark:bg-danger-900/10 rounded-lg">
            <div className="w-8 h-8 bg-danger-100 dark:bg-danger-900/20 rounded-lg flex items-center justify-center">
              <Shield className="w-4 h-4 text-danger-600" />
            </div>
            <div className="flex-1">
              <div className="text-xs text-slate-600 dark:text-slate-400">Stop Loss</div>
              <div className="font-semibold text-slate-900 dark:text-white">
                {formatters.currency(data.trade_setup.stop_loss)}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 bg-success-50 dark:bg-success-900/10 rounded-lg">
            <div className="w-8 h-8 bg-success-100 dark:bg-success-900/20 rounded-lg flex items-center justify-center">
              <Target className="w-4 h-4 text-success-600" />
            </div>
            <div className="flex-1">
              <div className="text-xs text-slate-600 dark:text-slate-400">Targets</div>
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

          <div className="text-center text-sm text-slate-600 dark:text-slate-400 pt-2">
            Risk:Reward = {data.trade_setup.risk_reward}
          </div>
        </div>
      </div>

      {/* Position Sizing */}
      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-200 dark:border-blue-800">
        <div className="text-sm font-medium text-blue-900 dark:text-blue-300 mb-2">
          Recommended Position Size (2% risk)
        </div>
        <div className="text-xs text-blue-700 dark:text-blue-400 space-y-1">
          <div>Shares: {data.position_sizing.shares}</div>
          <div>
            Value: {formatters.currency(data.position_sizing.position_value)}
          </div>
          <div>Risk: {formatters.currency(data.position_sizing.risk_amount)}</div>
        </div>
      </div>
    </Card>
  )
}