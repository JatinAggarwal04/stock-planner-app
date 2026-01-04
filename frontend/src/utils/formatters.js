//frontend/src/utils/formatters.js
export const formatters = {
  // Format Indian currency
  currency: (value) => {
    if (value === null || value === undefined) return '₹0.00'
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  },

  // Format large numbers (Lakhs/Crores)
  compactNumber: (value) => {
    if (value === null || value === undefined) return '0'
    
    if (value >= 10000000) {
      return `${(value / 10000000).toFixed(2)}Cr`
    } else if (value >= 100000) {
      return `${(value / 100000).toFixed(2)}L`
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(2)}K`
    }
    return value.toFixed(2)
  },

  // Format percentage
  percentage: (value, decimals = 2) => {
    if (value === null || value === undefined) return '0.00%'
    return `${value > 0 ? '+' : ''}${value.toFixed(decimals)}%`
  },

  // Format date
  date: (dateString) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  },

  // Format time
  time: (dateString) => {
    return new Date(dateString).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
    })
  },

  // Format datetime
  datetime: (dateString) => {
    const date = new Date(dateString)
    return `${formatters.date(dateString)} ${formatters.time(dateString)}`
  },
}
