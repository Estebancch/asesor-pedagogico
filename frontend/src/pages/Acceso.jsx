import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth.jsx'
import { Marca } from '../Layout.jsx'
import { Aviso, Boton, Campo, useDatos } from '../ui.jsx'

const DEMO = [['Docente', 'docente@demo.edu.co', 'Docente2026'], ['Estudiante', 'laura@demo.edu.co', 'Estudiante2026'], ['Estudiante con vacíos', 'andres@demo.edu.co', 'Estudiante2026']]

export default function Acceso() {
  const { usuario, entrar } = useAuth()
  const navegar = useNavigate()
  const ubicacion = useLocation()
  const { datos: info } = useDatos(() => api.get('/publico/proyecto'))
  const [modo, setModo] = useState('entrar')
  const [f, setF] = useState({ nombre: '', email: '', password: '', codigo: '' })
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  if (usuario) return <Navigate to={ubicacion.state?.desde || '/app'} replace />

  const enviar = async (e) => {
    e.preventDefault()
    setError(''); setOcupado(true)
    try {
      const r = modo === 'entrar'
        ? await api.post('/auth/login', { email: f.email, password: f.password }, { sinRedirigir: true })
        : await api.post('/auth/registro', f, { sinRedirigir: true })
      entrar(r)
      navegar(ubicacion.state?.desde || '/app', { replace: true })
    } catch (err) { setError(err.message) } finally { setOcupado(false) }
  }
  const cambiar = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <div className="flex min-h-screen flex-col items-center bg-papel px-4 py-10">
      <Link to="/"><Marca /></Link>
      <div className="mt-8 w-full max-w-md rounded-2xl border border-linea bg-white p-6 sm:p-8">
        <h1 className="text-2xl font-bold">{modo === 'entrar' ? 'Inicia sesión' : 'Crea tu cuenta de estudiante'}</h1>
        <form onSubmit={enviar} className="mt-5 space-y-4">
          {modo === 'registro' && <>
            <Campo etiqueta="Nombre completo"><input className="campo" required minLength={3} value={f.nombre} onChange={cambiar('nombre')} autoComplete="name" /></Campo>
            <Campo etiqueta="Código estudiantil" ayuda="Opcional"><input className="campo" value={f.codigo} onChange={cambiar('codigo')} /></Campo>
          </>}
          <Campo etiqueta="Correo"><input className="campo" type="email" required value={f.email} onChange={cambiar('email')} autoComplete="email" /></Campo>
          <Campo etiqueta="Contraseña" ayuda={modo === 'registro' ? 'Mínimo 8 caracteres, con letras y números.' : undefined}>
            <input className="campo" type="password" required value={f.password} onChange={cambiar('password')} autoComplete={modo === 'entrar' ? 'current-password' : 'new-password'} />
          </Campo>
          {error && <Aviso tono="grave">{error}</Aviso>}
          <Boton type="submit" ocupado={ocupado} className="w-full py-2.5">{modo === 'entrar' ? 'Iniciar sesión' : 'Crear cuenta'}</Boton>
        </form>
        {info?.registro_abierto !== false && (
          <p className="mt-5 text-center text-grafito">
            {modo === 'entrar' ? '¿Eres estudiante y no tienes cuenta? ' : '¿Ya tienes cuenta? '}
            <button className="font-medium text-petroleo underline" onClick={() => { setModo(modo === 'entrar' ? 'registro' : 'entrar'); setError('') }}>
              {modo === 'entrar' ? 'Crear cuenta' : 'Iniciar sesión'}
            </button>
          </p>
        )}
      </div>
      {info?.demo && modo === 'entrar' && (
        <div className="mt-5 w-full max-w-md rounded-xl border border-dashed border-linea bg-white/70 p-4">
          <p className="font-medium">Cuentas de demostración</p>
          <p className="text-sm text-grafito">Datos ficticios para recorrer la plataforma. Elige una para llenar el formulario.</p>
          <ul className="mt-2 space-y-1">
            {DEMO.map(([rol, email, clave]) => (
              <li key={email}><button className="text-left text-petroleo underline" onClick={() => setF({ ...f, email, password: clave })}>{rol}: {email}</button></li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
