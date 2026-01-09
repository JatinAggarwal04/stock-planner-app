import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, TrendingUp, TrendingDown, DollarSign } from 'lucide-react'
import { format } from 'date-fns'
import Button from '../ui/Button'
import Input from '../ui/Input'
import { formatters } from '../../utils/formatters'

export default function OrderPad({
    isOpen,
    onClose,
    symbol,
    currentPrice,
    onSubmit,
    initialType = 'BUY',
    loading = false
}) {
    const [type, setType] = useState(initialType)
    const [price, setPrice] = useState('')
    const [quantity, setQuantity] = useState('')
    const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'))

    // Reset form when opening
    useEffect(() => {
        if (isOpen) {
            setType(initialType)
            setPrice('')
            setQuantity('')
            setDate(format(new Date(), 'yyyy-MM-dd'))
        }
    }, [isOpen, initialType])

    const calculateTotal = () => {
        const p = parseFloat(price) || currentPrice
        const q = parseInt(quantity) || 0
        return p * q
    }

    const handleSubmit = () => {
        if (!quantity) return

        // Use current price if not specified
        const finalPrice = price ? parseFloat(price) : currentPrice

        onSubmit({
            type,
            price: finalPrice,
            quantity: parseInt(quantity),
            date: new Date(date).toISOString()
        })
    }

    if (!isOpen) return null

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center pointer-events-none">
                {/* Backdrop */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="absolute inset-0 bg-black/60 backdrop-blur-sm pointer-events-auto"
                />

                {/* Modal/Bottom Sheet */}
                <motion.div
                    initial={{ y: '100%' }}
                    animate={{ y: 0 }}
                    exit={{ y: '100%' }}
                    transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                    className="bg-white dark:bg-slate-900 w-full sm:max-w-md sm:rounded-2xl rounded-t-2xl shadow-2xl overflow-hidden pointer-events-auto sm:mb-8"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-slate-800">
                        <div>
                            <h3 className="font-bold text-lg text-slate-900 dark:text-white flex items-center gap-2">
                                <span className="font-mono">{symbol}</span>
                                <span className="text-sm font-normal text-slate-500 dark:text-slate-400">
                                    {formatters.currency(currentPrice)}
                                </span>
                            </h3>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors"
                        >
                            <X className="w-5 h-5 text-slate-500" />
                        </button>
                    </div>

                    {/* Toggle Type */}
                    <div className="grid grid-cols-2 p-4 gap-4">
                        <button
                            onClick={() => setType('BUY')}
                            className={`flex items-center justify-center gap-2 py-3 rounded-xl font-semibold transition-all ${type === 'BUY'
                                    ? 'bg-success-600 text-white shadow-lg shadow-success-600/20'
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                                }`}
                        >
                            <TrendingUp className="w-4 h-4" />
                            Buy
                        </button>
                        <button
                            onClick={() => setType('SELL')}
                            className={`flex items-center justify-center gap-2 py-3 rounded-xl font-semibold transition-all ${type === 'SELL'
                                    ? 'bg-danger-600 text-white shadow-lg shadow-danger-600/20'
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                                }`}
                        >
                            <TrendingDown className="w-4 h-4" />
                            Sell
                        </button>
                    </div>

                    {/* Form */}
                    <div className="p-4 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <Input
                                label="Quantity"
                                type="number"
                                value={quantity}
                                onChange={(e) => setQuantity(e.target.value)}
                                placeholder="0"
                                className="text-lg font-semibold"
                                autoFocus
                            />
                            <Input
                                label="Price (Optional)"
                                type="number"
                                value={price}
                                onChange={(e) => setPrice(e.target.value)}
                                placeholder={currentPrice.toString()}
                                className="text-lg font-semibold"
                            />
                        </div>

                        <Input
                            label="Date"
                            type="date"
                            value={date}
                            onChange={(e) => setDate(e.target.value)}
                        />

                        {/* Calculations */}
                        <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-800">
                            <div className="text-sm font-medium text-slate-500 dark:text-slate-400">
                                Avg. Value
                            </div>
                            <div className="text-xl font-bold text-slate-900 dark:text-white">
                                {formatters.currency(calculateTotal())}
                            </div>
                        </div>
                    </div>

                    {/* Footer Action */}
                    <div className="p-4 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900">
                        <Button
                            size="lg"
                            className="w-full text-lg shadow-xl"
                            variant={type === 'BUY' ? 'success' : 'danger'}
                            onClick={handleSubmit}
                            disabled={loading || !quantity || parseInt(quantity) <= 0}
                        >
                            {loading ? 'Processing...' : (
                                <>
                                    {type === 'BUY' ? 'Buy' : 'Short Sell'}
                                    <span className="font-mono ml-2">{symbol}</span>
                                </>
                            )}
                        </Button>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    )
}
