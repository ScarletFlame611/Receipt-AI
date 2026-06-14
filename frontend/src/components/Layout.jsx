import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { useTheme } from '../theme.jsx'

export default function Layout() {
  const { user, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <>
      <nav className="nav">
        <span className="brand">🧾 Receipt-AI</span>
        <NavLink to="/" end>Дашборд</NavLink>
        <NavLink to="/upload">Загрузить</NavLink>
        <NavLink to="/receipts">Чеки</NavLink>
        <NavLink to="/profile">Профиль</NavLink>
        {user?.is_admin && <NavLink to="/admin">Админка</NavLink>}
        <span className="spacer" />
        <button className="icon-btn" onClick={toggle} title="Переключить тему">
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
        <button className="ghost small" onClick={handleLogout}>Выйти</button>
      </nav>
      <div className="container">
        <Outlet />
      </div>
    </>
  )
}
