import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth.jsx'
import { Marca } from '../Layout.jsx'
import { Cargando, Regla, useDatos } from '../ui.jsx'

/* Portada pública: presenta el proyecto (abstract, objetivos, funcionalidades,
   tecnologías, aportes) y al equipo desarrollador. */
function Muestra() {
  // Un criterio evaluado, tal como lo ve el estudiante: lo más característico del producto.
  return (
    <div className="rounded-2xl border border-linea bg-white p-5 shadow-[0_18px_50px_-30px_rgba(18,41,46,.55)] sm:p-6">
      <p className="text-sm text-grafito">Así se lee una valoración</p>
      <p className="titulo mt-1 text-lg font-bold">Implementación de BFS y A* con heurística admisible</p>
      <p className="mt-0.5 text-sm text-grafito">Criterio con ponderación de 35 % · nivel asignado: Bueno</p>
      <blockquote className="mt-4 border-l-2 border-tinta/20 pl-3.5 text-[0.95rem] leading-relaxed">
        «A* usa una cola de prioridad con f = g + h, donde h es <mark className="cita">la heurística Manhattan, que es admisible porque nunca sobreestima el costo real</mark> en una cuadrícula sin diagonales.»
        <footer className="mt-1.5 text-sm text-grafito">informe.pdf, página 1 — cita verificada contra la entrega</footer>
      </blockquote>
      <div className="mt-5">
        <Regla nota={4.3} etiqueta="Nota del laboratorio" />
      </div>
      <p className="mt-3 text-sm text-grafito">La IA propone el nivel y cita la evidencia. La nota la calcula el servidor con la rúbrica y el docente la aprueba antes de publicarla.</p>
    </div>
  )
}

// Sin fotografía se muestran las iniciales (primera y última palabra del nombre)
const iniciales = (nombre) => { const p = nombre.trim().split(/\s+/); return ((p[0]?.[0] || '') + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase() }

export default function Inicio() {
  const { usuario } = useAuth()
  const { datos, error, cargando } = useDatos(() => api.get('/publico/proyecto'))
  const p = datos?.proyecto
  const destino = usuario ? '/app' : '/acceso'
  return (
    <div className="min-h-screen bg-papel">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 sm:px-8">
        <Marca />
        <Link to={destino} className="rounded-lg bg-tinta px-4 py-2 font-medium text-white hover:bg-petroleo-oscuro">{usuario ? 'Ir a mi panel' : 'Iniciar sesión'}</Link>
      </header>
      {cargando && <div className="mx-auto max-w-6xl px-8"><Cargando /></div>}
      {error && <p className="mx-auto max-w-6xl px-8 text-grave">{error}</p>}
      {p && (
        <main>
          <section className="mx-auto grid max-w-6xl items-center gap-10 px-5 pb-16 pt-8 sm:px-8 lg:grid-cols-[1.05fr_.95fr] lg:pt-14">
            <div>
              <p className="text-grafito">{p.institucion}</p>
              <h1 className="mt-4 text-[2.4rem] font-bold leading-[1.05] sm:text-[3.3rem]">Saber qué aprendiste, con la evidencia a la vista.</h1>
              <p className="mt-5 max-w-xl text-lg text-grafito">{p.lema}. Sube tu informe y tu código; cada criterio de la rúbrica se valora citando lo que entregaste.</p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link to={destino} className="inline-flex items-center gap-2 rounded-lg bg-petroleo px-5 py-3 text-lg font-medium text-white hover:bg-petroleo-oscuro">
                  {usuario ? 'Ir a mi panel' : 'Entrar a la plataforma'}<ArrowRight size={19} aria-hidden />
                </Link>
                <a href="#proyecto" className="rounded-lg border border-linea bg-white px-5 py-3 text-lg font-medium hover:border-petroleo">Conocer el proyecto</a>
              </div>
            </div>
            <Muestra />
          </section>

          <section id="proyecto" className="border-y border-linea bg-white">
            <div className="mx-auto grid max-w-6xl gap-10 px-5 py-14 sm:px-8 lg:grid-cols-[1.4fr_1fr]">
              <div>
                <h2 className="text-2xl font-bold">Resumen del proyecto</h2>
                <p className="mt-4 max-w-[68ch] text-[1.05rem] leading-relaxed">{p.abstract}</p>
              </div>
              <div>
                <h2 className="text-2xl font-bold">Objetivos</h2>
                <ul className="mt-4 space-y-3">
                  {p.objetivos.map((o, i) => <li key={i} className="border-l-2 border-petroleo pl-3.5">{o}</li>)}
                </ul>
              </div>
            </div>
          </section>

          <section className="mx-auto max-w-6xl px-5 py-14 sm:px-8">
            <h2 className="text-2xl font-bold">Qué hace la plataforma</h2>
            <ul className="mt-6 grid gap-x-10 gap-y-4 sm:grid-cols-2">
              {p.funcionalidades.map((f, i) => <li key={i} className="border-t border-linea pt-3.5">{f}</li>)}
            </ul>
          </section>

          <section className="bg-tinta text-white">
            <div className="mx-auto grid max-w-6xl gap-12 px-5 py-14 sm:px-8 lg:grid-cols-2">
              <div>
                <h2 className="text-2xl font-bold">Por qué se puede confiar en el resultado</h2>
                <ul className="mt-5 space-y-4">
                  {p.aportes.map((a, i) => <li key={i} className="border-l-2 border-resaltador pl-3.5 text-white/90">{a}</li>)}
                </ul>
              </div>
              <div>
                <h2 className="text-2xl font-bold">Tecnologías</h2>
                <ul className="mt-5 space-y-2.5 text-white/85">
                  {p.tecnologias.map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </div>
            </div>
          </section>

          <section id="equipo" className="mx-auto max-w-6xl px-5 py-14 sm:px-8">
            <h2 className="text-2xl font-bold">Equipo desarrollador</h2>
            <ul className="mt-7 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
              {datos.equipo.map((m) => (
                <li key={m.id} className="flex gap-4">
                  {m.foto
                    ? <img src={m.foto} alt={`Fotografía de ${m.nombre}`} className="h-24 w-24 shrink-0 rounded-xl object-cover" />
                    : <span className="titulo flex h-24 w-24 shrink-0 items-center justify-center rounded-xl bg-petroleo-suave text-3xl font-bold text-petroleo-oscuro" aria-hidden>{iniciales(m.nombre)}</span>}
                  <div className="min-w-0">
                    <p className="titulo text-lg font-bold">{m.nombre}</p>
                    <p className="text-petroleo-oscuro">{m.rol}</p>
                    {m.descripcion && <p className="mt-1 text-sm text-grafito">{m.descripcion}</p>}
                    {m.enlace && <a href={m.enlace} target="_blank" rel="noreferrer" className="mt-1 inline-block text-sm text-petroleo underline">Perfil</a>}
                  </div>
                </li>
              ))}
            </ul>
          </section>
          <footer className="border-t border-linea px-5 py-6 text-center text-sm text-grafito">
            Proyecto final de Profundización I: Inteligencia Artificial. Desarrollado con ingeniería de software aumentada por IA.
          </footer>
        </main>
      )}
    </div>
  )
}
