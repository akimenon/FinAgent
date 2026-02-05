import { useState, useEffect, useRef } from 'react'
import { Search, X, Loader2 } from 'lucide-react'
import { companiesApi } from '../../services/api'

/**
 * Shared ticker search component with type-ahead dropdown.
 * Used in Dashboard (via StockSearch wrapper), Portfolio add modal,
 * and Watchlist add-to-portfolio modal.
 *
 * Props:
 * - onSelect(symbol, name): Called when user picks a result
 * - placeholder: Input placeholder text
 * - compact: If true, uses smaller form-friendly styling (for modals)
 * - disabled: Disable the input
 * - className: Additional CSS classes for the wrapper
 */
export default function TickerSearch({
  onSelect,
  placeholder = 'Search by symbol or company name...',
  compact = false,
  disabled = false,
  className = '',
}) {
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
        inputRef.current &&
        !inputRef.current.contains(event.target)
      ) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (symbol, name) => {
    setQuery('')
    setResults([])
    setShowResults(false)
    onSelect(symbol, name)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && query.length > 0) {
      if (/^[A-Z]{1,5}$/i.test(query.trim())) {
        handleSelect(query.trim().toUpperCase(), '')
      } else if (results.length > 0) {
        handleSelect(results[0].symbol, results[0].name)
      }
    }
  }

  const inputClasses = compact
    ? 'w-full pl-10 pr-10 py-2 bg-slate-900 border border-slate-600 rounded-lg focus:outline-none focus:border-blue-500 text-sm disabled:opacity-50'
    : 'w-full pl-12 pr-12 py-4 bg-slate-800 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg'

  const iconSize = compact ? 'h-4 w-4' : 'h-5 w-5'
  const iconLeft = compact ? 'left-3' : 'left-4'
  const iconRight = compact ? 'right-3' : 'right-4'

  return (
    <div className={`relative ${className}`}>
      <div className="relative">
        <Search
          className={`absolute ${iconLeft} top-1/2 transform -translate-y-1/2 ${iconSize} text-slate-400`}
        />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setShowResults(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className={inputClasses}
        />
        {query && (
          <button
            onClick={() => {
              setQuery('')
              setResults([])
            }}
            className={`absolute ${iconRight} top-1/2 transform -translate-y-1/2`}
          >
            <X className={`${iconSize} text-slate-400 hover:text-white`} />
          </button>
        )}
      </div>

      {/* Results dropdown */}
      {showResults && (query.length > 0 || loading) && (
        <div
          ref={resultsRef}
          className="absolute z-50 w-full mt-1 bg-slate-800 border border-slate-600 rounded-lg shadow-xl max-h-60 overflow-y-auto"
        >
          {loading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
            </div>
          ) : results.length > 0 ? (
            <ul>
              {results.map((result) => (
                <li key={result.symbol}>
                  <button
                    onClick={() => handleSelect(result.symbol, result.name)}
                    className={`w-full hover:bg-slate-700 flex items-center justify-between text-left transition-colors ${
                      compact ? 'px-3 py-2 text-sm' : 'px-4 py-3'
                    }`}
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
            <div className={`text-center text-slate-400 ${compact ? 'px-3 py-4' : 'px-4 py-8'}`}>
              <p>No results found for "{query}"</p>
              <p className="text-sm mt-1">
                Try entering a stock symbol directly (e.g., AAPL)
              </p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
