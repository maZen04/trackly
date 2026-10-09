import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/AuthContext.jsx'

export default function Layout() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true" />
          Trackly
        </Link>
        <button className="btn btn-ghost" onClick={handleLogout}>
          Log out
        </button>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </div>
  )
}
