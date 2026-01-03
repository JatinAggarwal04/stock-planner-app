import { useState, useRef, useEffect } from 'react'
import { X, Send, Loader2, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { geminiService } from '../../services/geminiService'
import MessageBubble from './MessageBubble'
import StockContextChip from './StockContextChip'
import Button from '../ui/Button'

export default function ChatInterface({ onClose, context = 'general' }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        context.type === 'stock'
          ? `I'm analyzing ${context.symbol}. Current price is ₹${context.current_price}. How can I help you with this stock?`
          : "Hi! I'm TradeWise AI. I can help you analyze stocks, understand market trends, and answer your trading questions. What would you like to know?",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showContext, setShowContext] = useState(context.type === 'stock')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Initialize chat with context
    if (context.type === 'stock') {
      geminiService.resetChat()
      geminiService.startChat(context)
    } else {
      geminiService.resetChat()
      geminiService.startChat('general')
    }
  }, [context])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await geminiService.sendMessage(
        input,
        showContext && context.type === 'stock' ? context : null
      )

      const aiMessage = {
        role: 'assistant',
        content: response,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, aiMessage])
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: "I'm having trouble responding right now. Please try again.",
        timestamp: new Date(),
        error: true,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleContextToggle = () => {
    setShowContext(!showContext)
    geminiService.resetChat()
    if (!showContext && context.type === 'stock') {
      geminiService.startChat(context)
    } else {
      geminiService.startChat('general')
    }
  }

  const quickPrompts = [
    'What does the current analysis suggest?',
    'Should I buy or sell now?',
    'Explain the technical indicators',
    'What are the key risk factors?',
  ]

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        />

        {/* Chat Window */}
        <motion.div
          initial={{ opacity: 0, y: 100, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 100, scale: 0.9 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="relative w-full sm:max-w-2xl h-[100vh] sm:h-[80vh] bg-white dark:bg-dark-surface sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-dark-border bg-gradient-to-r from-primary-50 to-primary-100 dark:from-dark-surface dark:to-dark-card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center shadow-lg">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white">
                  TradeWise AI
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  Powered by Gemini 2.0 Flash
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-200 dark:hover:bg-dark-hover rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-slate-600 dark:text-slate-300" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}

            {loading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-slate-500"
              >
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Thinking...</span>
              </motion.div>
            )}

            {/* Quick Prompts (show only on first message) */}
            {messages.length === 1 && context.type === 'stock' && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="space-y-2"
              >
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Quick questions:
                </p>
                <div className="flex flex-wrap gap-2">
                  {quickPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInput(prompt)}
                      className="px-3 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg text-sm text-slate-700 dark:text-slate-300 transition-colors"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-slate-200 dark:border-dark-border p-4 bg-slate-50 dark:bg-slate-900">
            {/* Context Chip */}
            {context.type === 'stock' && (
              <StockContextChip
                symbol={context.symbol}
                show={showContext}
                onToggle={handleContextToggle}
              />
            )}

            {/* Input */}
            <div className="flex items-end gap-2">
              <div className="flex-1 bg-white dark:bg-dark-surface rounded-xl border-2 border-slate-200 dark:border-slate-700 focus-within:border-primary-500 transition-colors">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={
                    showContext && context.type === 'stock'
                      ? `Ask about ${context.symbol}...`
                      : 'Ask me anything about stocks...'
                  }
                  rows={1}
                  className="w-full px-4 py-3 bg-transparent resize-none outline-none text-slate-900 dark:text-white placeholder:text-slate-400"
                  style={{
                    maxHeight: '120px',
                    minHeight: '48px',
                  }}
                />
              </div>

              <Button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="h-12 w-12 p-0"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </Button>
            </div>

            {/* Disclaimer */}
            <p className="text-xs text-slate-500 dark:text-slate-500 mt-2 text-center">
              AI can make mistakes. This is not financial advice.
            </p>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}