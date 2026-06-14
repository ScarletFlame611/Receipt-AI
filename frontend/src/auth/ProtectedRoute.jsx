import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'

// Гейт для защищённых роутов. adminOnly — дополнительно требует прав админа.
export default function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="container muted">Загрузка…</div>
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  if (adminOnly && !user.is_admin) {
    return <Navigate to="/" replace />
  }
  return children
}
