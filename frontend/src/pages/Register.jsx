import { useNavigate } from 'react-router-dom'
import AuthForm from '../components/AuthForm.jsx'
import { useAuth } from '../lib/AuthContext.jsx'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()

  return (
    <AuthForm
      mode="register"
      onSubmit={async (email, password) => {
        await register(email, password)
        navigate('/', { replace: true })
      }}
    />
  )
}
