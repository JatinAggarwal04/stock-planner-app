import { motion } from 'framer-motion'
import { User, Bot } from 'lucide-react'
import { formatters } from '../../utils/formatters'

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isError = message.error

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser
            ? 'bg-primary-600'
            : isError
            ? 'bg-danger-600'
            : 'bg-gradient-to-br from-primary-500 to-primary-700'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message */}
      <div
        className={`flex-1 max-w-[80%] ${
          isUser ? 'items-end' : 'items-start'
        } flex flex-col gap-1`}
      >
        <div
          className={`px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-primary-600 text-white'
              : isError
              ? 'bg-danger-50 dark:bg-danger-900/20 text-danger-700 dark:text-danger-400 border border-danger-200 dark:border-danger-800'
              : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
          } ${isUser ? 'rounded-br-none' : 'rounded-bl-none'}`}
        >
          <p className="text-sm whitespace-pre-wrap break-words">
            {message.content}
          </p>
        </div>

        <span className="text-xs text-slate-500 dark:text-slate-500 px-2">
          {formatters.time(message.timestamp)}
        </span>
      </div>
    </motion.div>
  )
}