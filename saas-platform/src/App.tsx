import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Landing } from '@/pages/Landing'
import { Login } from '@/pages/Login'
import { Register } from '@/pages/Register'
import { Dashboard } from '@/pages/Dashboard'
import { Portfolio } from '@/pages/Portfolio'
import { MarketAnalysis } from '@/pages/MarketAnalysis'
import { Kondratiev } from '@/pages/Kondratiev'
import { ETFTracking } from '@/pages/ETFTracking'
import { AIAnalysis } from '@/pages/AIAnalysis'
import { Macro } from '@/pages/Macro'
import { Reports } from '@/pages/Reports'
import { Pricing } from '@/pages/Pricing'
import { Settings } from '@/pages/Settings'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/pricing" element={<Pricing />} />

      {/* Protected Routes */}
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/portfolio" element={<ProtectedRoute><Portfolio /></ProtectedRoute>} />
      <Route path="/market" element={<ProtectedRoute><MarketAnalysis /></ProtectedRoute>} />
      <Route path="/kondratiev" element={<ProtectedRoute><Kondratiev /></ProtectedRoute>} />
      <Route path="/etf" element={<ProtectedRoute><ETFTracking /></ProtectedRoute>} />
      <Route path="/ai-analysis" element={<ProtectedRoute><AIAnalysis /></ProtectedRoute>} />
      <Route path="/macro" element={<ProtectedRoute><Macro /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
