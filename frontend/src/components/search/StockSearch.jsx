import { useState, useEffect, useRef } from 'react'
import { Search, X, Loader2 } from 'lucide-react'
import { companiesApi } from '../../services/api'

export default function StockSearch({ onSelect }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const inputRef = useRef(null)
  const resultsRef = useRef(null)

  useEffect(() => {
    const searchCompanies = async () => {
      if (query.length < 1) {
        setResults([])
        return
      }

      setLoading(true)
      try {
        const response = await companiesApi.search(query)
        setResults(response.data.results || [])
      } catch (error) {
        console.error('Search error:', error)
        setResults([])
      } finally {
        setLoading(false)
      }
    }

    const debounce = setTimeout(searchCompanies, 300)
    return () => clearTimeout(debounce)
  }, [query])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        resultsRef.current &&
        !resultsRef.current.contains(event.target) &&
        !inputRef.current.contains(event.target)
      ) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (symbol) => {
    setQuery('')
    setResults([])
    setShowResults(false)
    onSelect(symbol)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && query.length > 0) {
      // If query looks like a valid symbol, go directly
      if (/^[A-Z]{1,5}$/i.test(query.trim())) {
        handleSelect(query.trim().toUpperCase())
      } else if (results.length > 0) {
        handleSelect(results[0].symbol)
      }
    }
  }

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setShowResults(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search by symbol or company name..."
          className="w-full pl-12 pr-12 py-4 bg-slate-800 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
        />
        {query && (
          <button
            onClick={() => {
              setQuery('')
              setResults([])
            }}
            className="absolute right-4 top-1/2 transform -translate-y-1/2"
          >
            <X className="h-5 w-5 text-slate-400 hover:text-white" />
          </button>
        )}
      </div>

      {/* Results dropdown */}
      {showResults && (query.length > 0 || loading) && (
        <div
          ref={resultsRef}
          className="absolute z-50 w-full mt-2 bg-slate-800 border border-slate-600 rounded-lg shadow-xl max-h-80 overflow-y-auto"
        >
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
            </div>
          ) : results.length > 0 ? (
            <ul>
              {results.map((result) => (
                <li key={result.symbol}>
                  <button
                    onClick={() => handleSelect(result.symbol)}
                    className="w-full px-4 py-3 hover:bg-slate-700 flex items-center justify-between text-left transition-colors"
                  >
                    <div>
                      <span className="font-semibold text-blue-400">
                        {result.symbol}
                      </span>
                      <span className="text-slate-400 ml-2">{result.name}</span>
                    </div>
                    <span className="text-xs text-slate-500">
                      {result.exchangeShortName}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : query.length > 0 ? (
            <div className="px-4 py-8 text-center text-slate-400">
              <p>No results found for "{query}"</p>
              <p className="text-sm mt-2">
                Try entering a stock symbol directly (e.g., AAPL)
              </p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
