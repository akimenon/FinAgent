import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import NavBar from './components/layout/NavBar'
import Dashboard from './pages/Dashboard'
import CompanyAnalysis from './pages/CompanyAnalysis'
import EarningsCalendar from './pages/EarningsCalendar'
import Watchlist from './pages/Watchlist'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-900">
        <NavBar />
        <main className="container mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analysis/:symbol" element={<CompanyAnalysis />} />
            <Route path="/earnings" element={<EarningsCalendar />} />
            <Route path="/watchlist" element={<Watchlist />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
