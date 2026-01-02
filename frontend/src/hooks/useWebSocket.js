import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { stockService } from '../services/stockService'

export function useRealtimePrice(symbol, interval = 5000) {
  const [price, setPrice] = useState(null)
  const [change, setChange] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['quote', symbol],
    queryFn: () => stockService.getQuote(symbol),
    refetchInterval: interval,
    enabled: !!symbol,
  })

  useEffect(() => {
    if (data) {
      setPrice(data.price)
      setChange(data.change_pct)
    }
  }, [data])

  return { price, change, isLoading }
}
