import TickerSearch from './TickerSearch'

/**
 * Dashboard stock search - wraps TickerSearch with Dashboard-specific styling.
 * Uses full-size (non-compact) mode for the hero search experience.
 */
export default function StockSearch({ onSelect }) {
  const handleSelect = (symbol) => {
    onSelect(symbol)
  }

  return (
    <TickerSearch
      onSelect={handleSelect}
      placeholder="Search by symbol or company name..."
    />
  )
}
