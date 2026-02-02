import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Companies API
export const companiesApi = {
  search: (query) => api.get('/companies/search', { params: { q: query } }),
  getCompany: (symbol) => api.get(`/companies/${symbol}`),
  getProfile: (symbol) => api.get(`/companies/${symbol}/profile`),
  getMarketMovers: () => api.get('/companies/market-movers'),
  getMarketIndices: () => api.get('/companies/market-indices'),
  getSectorStocks: (sector) => api.get(`/companies/sectors/${sector}`),
}

// Financials API
export const financialsApi = {
  getOverview: (symbol) => api.get(`/financials/${symbol}/overview`),
  getQuarterly: (symbol, limit = 5) =>
    api.get(`/financials/${symbol}/quarterly`, { params: { limit } }),
  getEstimates: (symbol) => api.get(`/financials/${symbol}/estimates`),
  getSurprises: (symbol, limit = 12) =>
    api.get(`/financials/${symbol}/surprises`, { params: { limit } }),
  getPriceHistory: (symbol, period = '1y') =>
    api.get(`/financials/${symbol}/price-history`, { params: { period } }),
  getGuidance: (symbol) => api.get(`/financials/${symbol}/guidance`),
  getAnalysis: (symbol) => api.get(`/financials/${symbol}/analysis`),
  getMarketFeed: (symbol) => api.get(`/financials/${symbol}/market-feed`),
  getDeepInsights: (symbol, refresh = false) =>
    api.get(`/financials/${symbol}/deep-insights`, { params: { refresh } }),
  getAnalystRatings: (symbol) => api.get(`/financials/${symbol}/analyst-ratings`),
  getEarningsCalendar: (days = 7) =>
    api.get('/financials/earnings-calendar', { params: { days } }),
}

// Agent API
export const agentApi = {
  query: (symbol, query) => api.post('/agent/query', { symbol, query }),
  analyze: (symbol, query = '') =>
    api.post('/agent/analyze', { symbol, query }),
  chat: (symbol, question) =>
    api.post('/agent/chat', { symbol, question }),

  // Streaming version using EventSource
  queryStream: (symbol, query, callbacks) => {
    const { onMessage, onError, onComplete } = callbacks

    const url = `${API_BASE_URL}/agent/query/stream?symbol=${encodeURIComponent(
      symbol
    )}&query=${encodeURIComponent(query)}`

    const eventSource = new EventSource(url)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)

        if (data.phase === 'complete' || data.phase === 'error') {
          eventSource.close()
          if (onComplete) onComplete(data)
        }
      } catch (e) {
        console.error('Error parsing SSE data:', e)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE Error:', error)
      eventSource.close()
      if (onError) onError(error)
    }

    return eventSource
  },
}

export default api
