import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'

export default function Profile() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div>
      <h2>Профиль</h2>
      <div className="card" style={{ maxWidth: 480 }}>
        <div className="field"><label>Email</label><div>{user.email}</div></div>
        <div className="field">
          <label>Роль</label>
          <div>{user.is_admin ? 'Администратор' : 'Пользователь'}</div>
        </div>
        <div className="field">
          <label>Статус</label>
          <div>{user.is_active ? 'Активен' : 'Заблокирован'}</div>
        </div>
        <div className="field">
          <label>Зарегистрирован</label>
          <div>{new Date(user.created_at).toLocaleString('ru-RU')}</div>
        </div>
        <button className="danger" onClick={handleLogout}>Выйти из аккаунта</button>
      </div>
    </div>
  )
}
