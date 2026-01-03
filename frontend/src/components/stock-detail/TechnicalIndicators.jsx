import { Activity, TrendingUp, BarChart3 } from 'lucide-react'
import Card from '../ui/Card'
import Badge from '../ui/Badge'

export default function TechnicalIndicators({ data }) {
  const indicators = [
    {
      name: 'RSI (14)',
      value: data.RSI,
      status: data.RSI > 70 ? 'Overbought' : data.RSI < 30 ? 'Oversold' : 'Neutral',
      color: data.RSI > 70 ? 'danger' : data.RSI < 30 ? 'success' : 'default',
      icon: Activity,
    },
    {
      name: 'MACD',
      value: data.MACD_Signal,
      status: data.MACD_Signal,
      color: data.MACD_Signal === 'Bullish' ? 'success' : 'danger',
      icon: TrendingUp,
    },
    {
      name: 'ADX',
      value: data.Trend_Strength_ADX,
      status: data.Trend_Strength_ADX > 25 ? 'Strong Trend' : 'Weak Trend',
      color: data.Trend_Strength_ADX > 25 ? 'success' : 'warning',
      icon: BarChart3,
    },
  ]

  return (
    <Card className="p-6">
      <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-6">
        Technical Indicators
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {indicators.map((indicator) => (
          <div
            key={indicator.name}
            className="p-4 bg-slate-50 dark:bg-slate-800 rounded-xl"
          >
            <div className="flex items-center gap-2 mb-3">
              <indicator.icon className="w-5 h-5 text-primary-600" />
              <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
                {indicator.name}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-slate-900 dark:text-white mb-1">
                  {typeof indicator.value === 'number'
                    ? indicator.value.toFixed(2)
                    : indicator.value}
                </div>
                <Badge variant={indicator.color} className="text-xs">
                  {indicator.status}
                </Badge>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Additional Details */}
      <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 pt-6 border-t border-slate-200 dark:border-slate-700">
        <div>
          <div className="text-xs text-slate-500 mb-1">Price vs SMA200</div>
          <div
            className={`text-lg font-semibold ${
              data.Price_vs_SMA200 > 0 ? 'text-success-600' : 'text-danger-600'
            }`}
          >
            {data.Price_vs_SMA200 > 0 ? '+' : ''}
            {data.Price_vs_SMA200.toFixed(2)}%
          </div>
        </div>

        <div>
          <div className="text-xs text-slate-500 mb-1">Volume Status</div>
          <Badge
            variant={
              data.Volume_Status === 'High'
                ? 'success'
                : data.Volume_Status === 'Normal'
                ? 'default'
                : 'warning'
            }
          >
            {data.Volume_Status}
          </Badge>
        </div>

        <div className="md:col-span-2">
          <div className="text-xs text-slate-500 mb-1">Interpretation</div>
          <p className="text-sm text-slate-700 dark:text-slate-300">
            {data.MACD_Signal === 'Bullish' && data.RSI < 70
              ? 'Positive momentum with room to grow'
              : data.MACD_Signal === 'Bearish' && data.RSI > 30
              ? 'Negative momentum, consider caution'
              : 'Mixed signals, wait for confirmation'}
          </p>
        </div>
      </div>
    </Card>
  )
}