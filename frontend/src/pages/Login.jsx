import { useNavigate } from 'react-router-dom'
import AuthForm from '../components/AuthForm.jsx'
import { useAuth } from '../lib/AuthContext.jsx'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()

  return (
    <AuthForm
      mode="login"
      onSubmit={async (email, password) => {
        await login(email, password)
        navigate('/', { replace: true })
      }}
    />
  )
}
