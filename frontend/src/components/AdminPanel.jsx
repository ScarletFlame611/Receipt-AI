import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'

export default function AdminPanel() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [error, setError] = useState('')

  async function load() {
    try {
      const [u, m] = await Promise.all([api.adminUsers(), api.adminMetrics()])
      setUsers(u)
      setMetrics(m)
    } catch (e) {
      setError(e.message)
    }
  }
  useEffect(() => { load() }, [])

  async function toggle(u) {
    if (u.is_active) await api.adminBlock(u.id)
    else await api.adminUnblock(u.id)
    load()
  }

  if (error) return <div className="error">{error}</div>
  if (!users || !metrics) return <div className="muted">Загрузка…</div>

  return (
    <div>
      <h2>Администрирование</h2>

      <div className="grid grid-3">
        <div className="card"><div className="muted">Пользователей</div><div className="stat">{metrics.users_total}</div></div>
        <div className="card"><div className="muted">Активных</div><div className="stat">{metrics.users_active}</div></div>
        <div className="card"><div className="muted">Чеков</div><div className="stat">{metrics.receipts_total}</div></div>
        <div className="card"><div className="muted">Позиций</div><div className="stat">{metrics.items_total}</div></div>
        <div className="card"><div className="muted">На проверке</div><div className="stat">{metrics.receipts_needs_review}</div></div>
      </div>

      <div className="card">
        <h3>Пользователи</h3>
        <table>
          <thead>
            <tr><th>ID</th><th>Email</th><th>Роль</th><th>Статус</th><th></th></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.id}</td>
                <td>{u.email}</td>
                <td>{u.is_admin ? 'админ' : 'юзер'}</td>
                <td>
                  <span className={`badge ${u.is_active ? 'ok' : 'failed'}`}>
                    {u.is_active ? 'активен' : 'заблокирован'}
                  </span>
                </td>
                <td>
                  {u.id !== me.id ? (
                    <button className={u.is_active ? 'danger small' : 'small'} onClick={() => toggle(u)}>
                      {u.is_active ? 'Заблокировать' : 'Разблокировать'}
                    </button>
                  ) : (
                    <span className="muted">это вы</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
