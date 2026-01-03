// ============================================
// FILE: src/components/stock-detail/ChartView.jsx
// ============================================
import { useState, useEffect, useRef } from 'react'
import { createChart, ColorType } from 'lightweight-charts'
import { useTheme } from '../../context/ThemeContext'
import { CHART_TYPES, TIME_RANGES } from '../../utils/constants'
import Card from '../ui/Card'
import Button from '../ui/Button'
import { LineChart, CandlestickChart, AreaChart } from 'lucide-react'

export default function ChartView({ symbol, currentPrice }) {
  const [chartType, setChartType] = useState(CHART_TYPES.CANDLESTICK)
  const [timeRange, setTimeRange] = useState('1M')
  const [chartData, setChartData] = useState([])
  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)
  const { theme } = useTheme()

  // Fetch historical data
  useEffect(() => {
    fetchHistoricalData()
  }, [symbol, timeRange])

  const fetchHistoricalData = async () => {
    try {
      // Generate mock data for demonstration
      const days = TIME_RANGES[timeRange] || 30
      const data = generateMockData(days, currentPrice)
      setChartData(data)
    } catch (error) {
      console.error('Failed to fetch chart data:', error)
    }
  }

  // Generate mock data for demonstration
  const generateMockData = (days, basePrice) => {
    const data = []
    let price = basePrice * 0.95
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - days)

    for (let i = 0; i < days; i++) {
      const date = new Date(startDate)
      date.setDate(date.getDate() + i)
      
      const change = (Math.random() - 0.48) * price * 0.02
      price += change

      const open = price
      const close = price + (Math.random() - 0.5) * price * 0.01
      const high = Math.max(open, close) * (1 + Math.random() * 0.01)
      const low = Math.min(open, close) * (1 - Math.random() * 0.01)

      data.push({
        time: Math.floor(date.getTime() / 1000),
        open: parseFloat(open.toFixed(2)),
        high: parseFloat(high.toFixed(2)),
        low: parseFloat(low.toFixed(2)),
        close: parseFloat(close.toFixed(2)),
        value: parseFloat(close.toFixed(2)),
      })
    }
    return data
  }

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current || chartData.length === 0) return

    const isDark = theme === 'dark'

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { type: ColorType.Solid, color: isDark ? '#1e293b' : '#ffffff' },
        textColor: isDark ? '#94a3b8' : '#64748b',
      },
      grid: {
        vertLines: { color: isDark ? '#334155' : '#e2e8f0' },
        horzLines: { color: isDark ? '#334155' : '#e2e8f0' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: isDark ? '#334155' : '#e2e8f0',
      },
      timeScale: {
        borderColor: isDark ? '#334155' : '#e2e8f0',
        timeVisible: true,
      },
    })

    let series

    if (chartType === CHART_TYPES.CANDLESTICK) {
      series = chart.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#ef4444',
        borderUpColor: '#10b981',
        borderDownColor: '#ef4444',
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
      })
      series.setData(chartData)
    } else if (chartType === CHART_TYPES.LINE) {
      series = chart.addLineSeries({
        color: '#3b82f6',
        lineWidth: 2,
      })
      series.setData(chartData.map(d => ({ time: d.time, value: d.close })))
    } else if (chartType === CHART_TYPES.AREA) {
      series = chart.addAreaSeries({
        topColor: 'rgba(59, 130, 246, 0.4)',
        bottomColor: 'rgba(59, 130, 246, 0.0)',
        lineColor: '#3b82f6',
        lineWidth: 2,
      })
      series.setData(chartData.map(d => ({ time: d.time, value: d.close })))
    }

    chart.timeScale().fitContent()

    chartRef.current = chart
    seriesRef.current = series

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [chartData, chartType, theme])

  return (
    <Card className="p-6">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        {/* Chart Type */}
        <div className="flex items-center gap-2">
          <Button
            variant={chartType === CHART_TYPES.CANDLESTICK ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setChartType(CHART_TYPES.CANDLESTICK)}
          >
            <CandlestickChart className="w-4 h-4" />
          </Button>
          <Button
            variant={chartType === CHART_TYPES.LINE ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setChartType(CHART_TYPES.LINE)}
          >
            <LineChart className="w-4 h-4" />
          </Button>
          <Button
            variant={chartType === CHART_TYPES.AREA ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setChartType(CHART_TYPES.AREA)}
          >
            <AreaChart className="w-4 h-4" />
          </Button>
        </div>

        {/* Time Range */}
        <div className="flex items-center gap-2">
          {Object.keys(TIME_RANGES).map((range) => (
            <Button
              key={range}
              variant={timeRange === range ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setTimeRange(range)}
            >
              {range}
            </Button>
          ))}
        </div>
      </div>

      {/* Chart Container */}
      <div ref={chartContainerRef} className="w-full" />
    </Card>
  )
}