import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, token } from './api'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function ProveedorAuth({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(Boolean(token.leer()))

  useEffect(() => {
    if (token.leer()) api.get('/auth/yo', { sinRedirigir: true }).then(setUsuario).catch(() => token.guardar('')).finally(() => setCargando(false))
    const vencida = () => setUsuario(null)
    window.addEventListener('asesor:sesion-vencida', vencida)
    return () => window.removeEventListener('asesor:sesion-vencida', vencida)
  }, [])

  const entrar = useCallback((respuesta) => { token.guardar(respuesta.token); setUsuario(respuesta.usuario) }, [])
  const salir = useCallback(() => { token.guardar(''); setUsuario(null) }, [])
  const esDocente = usuario?.rol === 'docente' || usuario?.rol === 'admin'
  return <Ctx.Provider value={{ usuario, cargando, entrar, salir, esDocente, esAdmin: usuario?.rol === 'admin' }}>{children}</Ctx.Provider>
}
