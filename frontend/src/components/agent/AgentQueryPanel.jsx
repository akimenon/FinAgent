import { useState } from 'react'
import { Send, Loader2, Bot, User } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { agentApi } from '../../services/api'

export default function AgentQueryPanel({ symbol }) {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [agentProgress, setAgentProgress] = useState([])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim() || loading) return

    const userMessage = query.trim()
    setQuery('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)
    setAgentProgress([])

    try {
      agentApi.queryStream(symbol, userMessage, {
        onMessage: (update) => {
          setAgentProgress((prev) => [...prev, update])

          if (update.phase === 'complete' && update.result) {
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: update.result.synthesis,
                data: update.result,
              },
            ])
            setLoading(false)
            setAgentProgress([])
          } else if (update.phase === 'error') {
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: `Error: ${update.message}`,
                error: true,
              },
            ])
            setLoading(false)
            setAgentProgress([])
          }
        },
        onError: (err) => {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: 'Failed to connect to analysis service',
              error: true,
            },
          ])
          setLoading(false)
          setAgentProgress([])
        },
      })
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: err.message, error: true },
      ])
      setLoading(false)
    }
  }

  const suggestedQueries = [
    'What are the key concerns for this stock?',
    'How consistent is the earnings growth?',
    'Compare margins over the last 4 quarters',
    'Is the company meeting guidance?',
  ]

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700">
      <div className="p-4 border-b border-slate-700">
        <h3 className="text-lg font-semibold flex items-center">
          <Bot className="h-5 w-5 mr-2 text-purple-500" />
          Ask the AI Agents
        </h3>
        <p className="text-sm text-slate-400 mt-1">
          Ask questions about {symbol} and our multi-agent system will analyze
          the data
        </p>
      </div>

      {/* Messages */}
      <div className="p-4 min-h-[200px] max-h-[400px] overflow-y-auto space-y-4">
        {messages.length === 0 && !loading && (
          <div className="text-center py-8">
            <p className="text-slate-400 mb-4">Suggested questions:</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {suggestedQueries.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setQuery(q)}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-full text-sm transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600'
                  : msg.error
                  ? 'bg-red-900/50'
                  : 'bg-slate-700'
              }`}
            >
              <div className="flex items-center gap-2 mb-1 text-xs text-slate-400">
                {msg.role === 'user' ? (
                  <>
                    <User className="h-3 w-3" /> You
                  </>
                ) : (
                  <>
                    <Bot className="h-3 w-3" /> AI Agents
                  </>
                )}
              </div>
              {msg.role === 'user' ? (
                <div className="text-sm">{msg.content}</div>
              ) : (
                <div className="text-sm ai-analysis">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Agent Progress */}
        {loading && agentProgress.length > 0 && (
          <div className="space-y-2">
            {agentProgress.map((status, i) => (
              <div
                key={i}
                className="flex items-center space-x-2 text-sm text-slate-400"
              >
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                <span>
                  <span className="font-medium">{status.agent}:</span>{' '}
                  {status.message}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about this stock..."
            disabled={loading}
            className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!query.trim() || loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
