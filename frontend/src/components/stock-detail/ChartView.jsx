
// FILE: src/components/stock-detail/ChartView.jsx

import { useState, useEffect, useRef } from 'react'
import { createChart, ColorType } from 'lightweight-charts'
import { useTheme } from '../../context/ThemeContext'
import { CHART_TYPES, TIME_RANGES } from '../../utils/constants'
import { stockService } from '../../services/stockService'
import Card from '../ui/Card'
import Button from '../ui/Button'
import { LineChart, CandlestickChart, AreaChart } from 'lucide-react'

const EXTENDED_RANGES = ['1D', '1W', '1M', '3M', '1Y', '5Y', 'All']

export default function ChartView({ symbol, timeRange, onTimeRangeChange, onPriceChange, currentPrice }) {
  const [chartType, setChartType] = useState(CHART_TYPES.AREA)
  const [chartData, setChartData] = useState([])
  const [markers, setMarkers] = useState([])
  const [prevClose, setPrevClose] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)
  const { theme } = useTheme()

  // Fetch historical data
  useEffect(() => {
    const fetchHistoricalData = async () => {
      setIsLoading(true)
      try {
        const response = await stockService.getHistory(symbol, timeRange)
        setChartData(response.data)
        setPrevClose(response.meta.previous_close || null)

        // Process Markers (Dividends/Splits)
        const eventMarkers = response.events.map(event => ({
          time: event.time,
          position: 'aboveBar',
          color: event.type === 'DIVIDEND' ? '#10b981' : '#3b82f6',
          shape: event.type === 'DIVIDEND' ? 'circle' : 'square',
          text: event.type === 'DIVIDEND' ? 'D' : 'S',
          size: 1, // small size
        }))
        setMarkers(eventMarkers)

        // Calculate and report price change
        if (response.data.length > 0) {
          const latestClose = response.data[response.data.length - 1].close
          const referencePrice = response.meta.previous_close || response.data[0].open

          const change = latestClose - referencePrice
          const changePercent = (change / referencePrice) * 100

          onPriceChange({
            change,
            changePercent,
            currentPrice: latestClose
          })
        }
      } catch (error) {
        console.error('Failed to fetch chart data:', error)
      } finally {
        setIsLoading(false)
      }
    }

    if (symbol) {
      fetchHistoricalData()
    }
  }, [symbol, timeRange, onPriceChange])

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return

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
        secondsVisible: false,
        tickMarkFormatter: (time, tickMarkType, locale) => {
          // Use India Standard Time (IST) explicitly
          const date = new Date(time * 1000);
          const options = { timeZone: 'Asia/Kolkata' };

          // TickMarkType: 0=Year, 1=Month, 2=DayOfMonth, 3=Time, 4=TimeWithSeconds

          // Year (0) or Month (1)
          if (tickMarkType === 0 || tickMarkType === 1) {
            return date.toLocaleDateString('en-IN', { ...options, month: 'short', year: 'numeric' });
          }
          // Day (2)
          if (tickMarkType === 2) {
            return date.toLocaleDateString('en-IN', { ...options, day: 'numeric', month: 'short', year: '2-digit' });
          }
          // Time (3 or 4)
          return date.toLocaleTimeString('en-IN', { ...options, hour: '2-digit', minute: '2-digit', hour12: false });
        },
      },
      localization: {
        timeFormatter: (timestamp) => {
          return new Date(timestamp * 1000).toLocaleString('en-IN', {
            timeZone: 'Asia/Kolkata',
            hour: '2-digit',
            minute: '2-digit',
            day: '2-digit',
            month: 'short',
            year: 'numeric',
          })
        },
      },
    })

    let series

    // Determine color based on price change
    let mainColor = '#64748b' // Default grey
    if (chartData.length > 0) {
      const firstPrice = chartData[0].close || chartData[0].value
      const lastPrice = chartData[chartData.length - 1].close || chartData[chartData.length - 1].value

      if (lastPrice > firstPrice) mainColor = '#10b981' // Green
      else if (lastPrice < firstPrice) mainColor = '#ef4444' // Red
    }

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
        color: mainColor,
        lineWidth: 2,
      })
      series.setData(chartData.map(d => ({ time: d.time, value: d.close })))
    } else if (chartType === CHART_TYPES.AREA) {
      series = chart.addAreaSeries({
        topColor: mainColor.replace(')', ', 0.4)').replace('rgb', 'rgba').replace('#10b981', 'rgba(16, 185, 129, 0.4)').replace('#ef4444', 'rgba(239, 68, 68, 0.4)').replace('#64748b', 'rgba(100, 116, 139, 0.4)'),
        bottomColor: mainColor.replace(')', ', 0.0)').replace('rgb', 'rgba').replace('#10b981', 'rgba(16, 185, 129, 0.0)').replace('#ef4444', 'rgba(239, 68, 68, 0.0)').replace('#64748b', 'rgba(100, 116, 139, 0.0)'),
        lineColor: mainColor,
        lineWidth: 2,
      })
      series.setData(chartData.map(d => ({ time: d.time, value: d.close })))
    }

    // Add Previous Close Line (The "Last Closing" Line)
    if (chartData.length > 0) {
      // Use meta value if available, otherwise fallback to first open
      const referencePrice = prevClose || chartData[0].open || chartData[0].value || chartData[0].close;

      series.createPriceLine({
        price: referencePrice,
        color: '#fbbf24', // Amber/Yellow for reference
        lineWidth: 1,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: 'Prev Close',
      });
    }

    // Set markers if any
    if (markers.length > 0) {
      series.setMarkers(markers)
    }

    if (chartData.length > 0) {
      chart.timeScale().fitContent()
    }

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
  }, [chartData, chartType, theme, markers])

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
        <div className="flex items-center gap-2 overflow-x-auto pb-2 sm:pb-0">
          {EXTENDED_RANGES.map((range) => (
            <Button
              key={range}
              variant={timeRange === range ? 'primary' : 'outline'}
              size="sm"
              onClick={() => onTimeRangeChange(range)}
              className="whitespace-nowrap"
            >
              {range}
            </Button>
          ))}
        </div>
      </div>

      {/* Chart Container */}
      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-slate-900/50 z-10 backdrop-blur-sm rounded-lg">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full" />
      </div>

      {/* Legend for Markers */}
      <div className="mt-4 flex gap-4 text-xs text-slate-500 justify-end">
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span> Dividends
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-sm bg-blue-500 inline-block"></span> Splits
        </div>
      </div>
    </Card>
  )
}