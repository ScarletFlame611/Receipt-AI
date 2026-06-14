import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './auth/ProtectedRoute.jsx'
import Layout from './components/Layout.jsx'
import Login from './components/Login.jsx'
import Register from './components/Register.jsx'
import PasswordReset from './components/PasswordReset.jsx'
import Dashboard from './components/Dashboard.jsx'
import UploadReceipt from './components/UploadReceipt.jsx'
import ReceiptList from './components/ReceiptList.jsx'
import ReceiptReview from './components/ReceiptReview.jsx'
import Profile from './components/Profile.jsx'
import AdminPanel from './components/AdminPanel.jsx'

export default function App() {
  return (
    <Routes>
      {/* Публичные роуты */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/reset" element={<PasswordReset />} />

      {/* Защищённые роуты под общим Layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="/upload" element={<UploadReceipt />} />
        <Route path="/receipts" element={<ReceiptList />} />
        <Route path="/receipts/:id" element={<ReceiptReview />} />
        <Route path="/profile" element={<Profile />} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute adminOnly>
              <AdminPanel />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
