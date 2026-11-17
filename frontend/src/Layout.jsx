import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { BookOpenCheck, ClipboardCheck, FileBarChart, FolderOpen, Home, LogOut, Menu, Network, Settings, X } from 'lucide-react'
import { useAuth } from './auth.jsx'

export function Marca({ clara = false }) {
  return (
    <span className="flex items-center gap-2.5">
      <img src="/favicon.svg" alt="" className="h-8 w-8" />
      <span className={`titulo text-[1.05rem] font-bold leading-tight ${clara ? 'text-white' : 'text-tinta'}`}>Asesor Pedagógico<br /><span className="font-medium opacity-80">Inteligente</span></span>
    </span>
  )
}

export default function Layout({ children }) {
  const { usuario, salir, esDocente, esAdmin } = useAuth()
  const [abierto, setAbierto] = useState(false)
  const navegar = useNavigate()
  const items = esDocente
    ? [['/app', 'Inicio', Home, true], ['/app/revision', 'Revisión de evaluaciones', ClipboardCheck], ['/app/laboratorios', 'Laboratorios y rúbricas', BookOpenCheck],
       ['/app/portafolio', 'Portafolios', FolderOpen], ...(esAdmin ? [['/app/admin', 'Administración', Settings]] : [])]
    : [['/app', 'Inicio', Home, true], ['/app/portafolio', 'Mi portafolio', FolderOpen], ['/app/informe', 'Informe integral', FileBarChart], ['/app/mapa', 'Mapa de competencias', Network]]
  const rol = { admin: 'Administración', docente: 'Docente', estudiante: 'Estudiante' }[usuario.rol]

  const nav = (
    <nav className="flex flex-1 flex-col gap-1" aria-label="Principal">
      {items.map(([a, texto, Icono, exacto]) => (
        <NavLink key={a} to={a} end={exacto} onClick={() => setAbierto(false)}
          className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 font-medium ${isActive ? 'bg-white/15 text-white' : 'text-white/75 hover:bg-white/10 hover:text-white'}`}>
          <Icono size={19} aria-hidden />{texto}
        </NavLink>
      ))}
      <Link to="/" className="mt-auto rounded-lg px-3 py-2 text-sm text-white/65 hover:text-white">Acerca del proyecto y el equipo</Link>
      <div className="border-t border-white/15 pt-3">
        <p className="truncate px-3 font-medium text-white">{usuario.nombre}</p>
        <p className="px-3 text-sm text-white/65">{rol}</p>
        <button onClick={() => { salir(); navegar('/') }} className="mt-2 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-white/75 hover:bg-white/10 hover:text-white">
          <LogOut size={18} aria-hidden />Cerrar sesión
        </button>
      </div>
    </nav>
  )
  return (
    <div className="min-h-screen lg:flex">
      <aside className="no-imprimir hidden w-64 shrink-0 flex-col gap-6 bg-tinta p-4 lg:sticky lg:top-0 lg:flex lg:h-screen">
        <Link to="/app" className="px-1 pt-1"><Marca clara /></Link>
        {nav}
      </aside>
      <div className="no-imprimir flex items-center justify-between bg-tinta px-4 py-3 lg:hidden">
        <Link to="/app"><Marca clara /></Link>
        <button onClick={() => setAbierto(!abierto)} aria-label={abierto ? 'Cerrar menú' : 'Abrir menú'} aria-expanded={abierto} className="rounded-md p-2 text-white">
          {abierto ? <X /> : <Menu />}
        </button>
      </div>
      {abierto && <div className="no-imprimir flex min-h-[70vh] flex-col bg-tinta px-4 pb-4 lg:hidden">{nav}</div>}
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  )
}
