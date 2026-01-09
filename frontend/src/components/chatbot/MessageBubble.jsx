import { motion } from 'framer-motion'
import { User, Bot } from 'lucide-react'
import { formatters } from '../../utils/formatters'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

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
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUser
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
        className={`flex-1 max-w-[80%] ${isUser ? 'items-end' : 'items-start'
          } flex flex-col gap-1`}
      >
        <div
          className={`px-4 py-3 rounded-2xl ${isUser
            ? 'bg-primary-600 text-white'
            : isError
              ? 'bg-danger-50 dark:bg-danger-900/20 text-danger-700 dark:text-danger-400 border border-danger-200 dark:border-danger-800'
              : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
            } ${isUser ? 'rounded-br-none' : 'rounded-bl-none'}`}
        >
          <div className={`text-sm ${isUser ? '' : 'markdown-body'}`}>
            {isUser ? (
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  table: ({ node, ...props }) => (
                    <div className="overflow-x-auto my-2">
                      <table className="min-w-full border-collapse border border-slate-300 dark:border-slate-700 text-sm" {...props} />
                    </div>
                  ),
                  th: ({ node, ...props }) => <th className="border border-slate-300 dark:border-slate-700 px-2 py-1 bg-slate-200 dark:bg-slate-700 font-semibold" {...props} />,
                  td: ({ node, ...props }) => <td className="border border-slate-300 dark:border-slate-700 px-2 py-1" {...props} />,
                  h3: ({ node, ...props }) => <h3 className="font-bold text-base mt-2 mb-1" {...props} />,
                  ul: ({ node, ...props }) => <ul className="list-disc pl-4 my-2 space-y-1" {...props} />,
                  li: ({ node, ...props }) => <li className="" {...props} />,
                  strong: ({ node, ...props }) => <strong className="font-bold text-slate-900 dark:text-white" {...props} />,
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>
        </div>

        <span className="text-xs text-slate-500 dark:text-slate-500 px-2">
          {formatters.time(message.timestamp)}
        </span>
      </div>
    </motion.div>
  )
}