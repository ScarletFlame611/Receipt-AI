import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'

// Два шага: запросить токен по email, затем подтвердить новый пароль токеном.
export default function PasswordReset() {
  const [step, setStep] = useState('request')
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function requestReset(e) {
    e.preventDefault()
    setError(''); setMessage(''); setBusy(true)
    try {
      const res = await api.requestReset(email)
      setMessage(res.detail || 'Если email зарегистрирован, письмо отправлено')
      setStep('confirm')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function confirmReset(e) {
    e.preventDefault()
    setError(''); setMessage(''); setBusy(true)
    try {
      await api.confirmReset(token, newPassword)
      setMessage('Пароль обновлён. Теперь можно войти.')
      setStep('done')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <h2>Сброс пароля</h2>

        {step === 'request' && (
          <form onSubmit={requestReset}>
            <div className="field">
              <label>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <button type="submit" disabled={busy} style={{ width: '100%' }}>
              {busy ? 'Отправка…' : 'Отправить токен'}
            </button>
          </form>
        )}

        {step === 'confirm' && (
          <form onSubmit={confirmReset}>
            <p className="muted">Введите токен из письма и новый пароль.</p>
            <div className="field">
              <label>Токен</label>
              <input value={token} onChange={(e) => setToken(e.target.value)} required />
            </div>
            <div className="field">
              <label>Новый пароль</label>
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
            </div>
            <button type="submit" disabled={busy} style={{ width: '100%' }}>
              {busy ? 'Сохранение…' : 'Сменить пароль'}
            </button>
          </form>
        )}

        {message && <div className="success-msg">{message}</div>}
        {error && <div className="error">{error}</div>}

        <p className="muted" style={{ marginTop: 14 }}>
          <Link to="/login">Вернуться ко входу</Link>
        </p>
      </div>
    </div>
  )
}
