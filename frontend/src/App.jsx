import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import NavBar from './components/layout/NavBar'
import Dashboard from './pages/Dashboard'
import CompanyAnalysis from './pages/CompanyAnalysis'
import EarningsCalendar from './pages/EarningsCalendar'
import Watchlist from './pages/Watchlist'
import Portfolio from './pages/Portfolio'
import { portfolioApi } from './services/api'

function App() {
  const [widescreen, setWidescreen] = useState(() => {
    return localStorage.getItem('finagent-widescreen') === 'true'
  })

  // Take a daily portfolio snapshot on app load (fire-and-forget)
  useEffect(() => {
    portfolioApi.takeSnapshot().catch(() => {})
  }, [])

  return (
    <Router>
      <div className="min-h-screen">
        <NavBar widescreen={widescreen} setWidescreen={setWidescreen} />
        <main className={`mx-auto py-6 transition-all duration-300 ${
          widescreen ? 'max-w-[2400px] px-6' : 'max-w-7xl px-4'
        }`}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analysis/:symbol" element={<CompanyAnalysis />} />
            <Route path="/earnings" element={<EarningsCalendar />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/portfolio" element={<Portfolio />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
