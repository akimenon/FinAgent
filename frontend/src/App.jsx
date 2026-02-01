import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import NavBar from './components/layout/NavBar'
import Dashboard from './pages/Dashboard'
import CompanyAnalysis from './pages/CompanyAnalysis'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-900">
        <NavBar />
        <main className="container mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analysis/:symbol" element={<CompanyAnalysis />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
