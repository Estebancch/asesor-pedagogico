import { Link, useParams } from 'react-router-dom'
import { Download, FileText, FolderArchive, GitBranch, MonitorPlay, Presentation } from 'lucide-react'
import { ESTADOS, api, estadoOculto, fmtFecha, fmtNota } from '../api'
import { useAuth } from '../auth.jsx'
import { Aviso, Cargando, Estado, Pagina, Vacio, useDatos } from '../ui.jsx'

export function Evidencias({ e }) {
  const item = (Icono, texto, onClick, href) => (
    <li className="flex items-center gap-2">
      <Icono size={16} className="shrink-0 text-grafito" aria-hidden />
      {href ? <a href={href} target="_blank" rel="noreferrer" className="truncate text-petroleo underline">{texto}</a>
        : <button onClick={onClick} className="flex min-w-0 items-center gap-1.5 text-petroleo underline"><span className="truncate">{texto}</span><Download size={14} aria-hidden /></button>}
    </li>
  )
  return (
    <ul className="space-y-1 text-[0.95rem]">
      {e.informe && item(FileText, e.informe.nombre, () => api.descargar(`/archivos/${e.informe.id}`, e.informe.nombre))}
      {e.codigo && item(FolderArchive, e.codigo.nombre, () => api.descargar(`/archivos/${e.codigo.id}`, e.codigo.nombre))}
      {e.repo_url && item(GitBranch, e.repo_url.replace('https://github.com/', '') + (e.repo_commit ? ` @ ${e.repo_commit.slice(0, 7)}` : ''), null, e.repo_url)}
      {e.presentacion && item(Presentation, e.presentacion.nombre, () => api.descargar(`/archivos/${e.presentacion.id}`, e.presentacion.nombre))}
      {e.presentacion_url && item(Presentation, 'Presentación en línea', null, e.presentacion_url)}
      {e.video_url && item(MonitorPlay, 'Video', null, e.video_url)}
    </ul>
  )
}

function PortafolioEstudiante({ estudianteId }) {
  const { esDocente } = useAuth()
  const { datos, error, cargando } = useDatos(() => api.get(`/portafolio${estudianteId ? `?estudiante_id=${estudianteId}` : ''}`), [estudianteId])
  if (cargando) return <Pagina titulo="Portafolio"><Cargando /></Pagina>
  if (error) return <Pagina titulo="Portafolio"><Aviso tono="grave">{error}</Aviso></Pagina>
  const est = datos.estudiante
  return (
    <Pagina titulo={esDocente ? est.nombre : 'Mi portafolio'}
      migas={esDocente && <Link to="/app/portafolio" className="underline">Portafolios</Link>}
      bajada={esDocente ? `${est.email}${est.codigo ? ` · código ${est.codigo}` : ''}` : 'Tus trabajos de los cortes 1 y 2, cada uno con la rúbrica con la que se evaluó.'}
      acciones={esDocente && <>
        <Link to={`/app/informe/${est.id}`} className="rounded-lg border border-linea bg-white px-3.5 py-2 font-medium hover:border-petroleo">Informe integral</Link>
        <Link to={`/app/mapa/${est.id}`} className="rounded-lg border border-linea bg-white px-3.5 py-2 font-medium hover:border-petroleo">Mapa de competencias</Link>
      </>}>
      <div className="space-y-8">
        {datos.cohortes.map((c) => (
          <section key={c.id}>
            <h2 className="text-xl font-bold">{c.nombre}{c.periodo && <span className="ml-2 text-base font-normal text-grafito">{c.periodo}</span>}</h2>
            {c.laboratorios.length === 0 && <p className="mt-2 text-grafito">Este corte aún no tiene laboratorios.</p>}
            <div className="mt-3 space-y-3">
              {c.laboratorios.map((l) => {
                const e = l.entregas[0]
                const ev = e?.evaluaciones.at(-1)
                return (
                  <article key={l.id} className="rounded-xl border border-linea bg-white p-4 sm:p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm text-grafito">Laboratorio {l.orden}{l.fecha && ` · ${fmtFecha(l.fecha)}`}{l.rubrica ? ` · rúbrica v${l.rubrica.version}` : ' · sin rúbrica validada'}</p>
                        <h3 className="text-lg font-bold"><Link to={`/app/laboratorios/${l.id}`} className="hover:underline">{l.titulo}</Link></h3>
                      </div>
                      {!e && <Link to={`/app/laboratorios/${l.id}`} className="rounded-lg bg-petroleo px-3.5 py-2 font-medium text-white hover:bg-petroleo-oscuro">{esDocente ? 'Cargar entrega' : 'Entregar'}</Link>}
                    </div>
                    {e && (
                      <div className="mt-3 grid gap-4 border-t border-linea pt-3 sm:grid-cols-[1fr_auto]">
                        <div className="min-w-0">
                          <p className="mb-1.5 text-sm text-grafito">Entrega {e.numero} · {fmtFecha(e.creado_en)}{l.entregas.length > 1 && ` · ${l.entregas.length} intentos`}</p>
                          <Evidencias e={e} />
                        </div>
                        <div className="sm:text-right">
                          {ev ? <>
                            <Estado valor={ev.visible || esDocente ? ev.estado : estadoOculto(ev.estado)} />
                            {ev.visible && ev.nota != null && <p className="num titulo mt-1.5 text-2xl font-bold">{fmtNota(ev.nota)}</p>}
                            {!ev.visible && !esDocente && ev.estado !== 'error' && <p className="mt-1.5 max-w-[16rem] text-sm text-grafito sm:ml-auto">{['preliminar', 'aprobada'].includes(ev.estado) ? 'Tu docente la está revisando.' : ESTADOS[ev.estado]?.texto}</p>}
                            {(ev.visible || esDocente) && <p className="mt-1"><Link to={`/app/evaluaciones/${ev.id}`} className="font-medium text-petroleo underline">Ver evaluación</Link></p>}
                          </> : <Link to={`/app/laboratorios/${l.id}`} className="font-medium text-petroleo underline">Evaluar esta entrega</Link>}
                        </div>
                      </div>
                    )}
                  </article>
                )
              })}
            </div>
          </section>
        ))}
      </div>
    </Pagina>
  )
}

function Matriz() {
  const { datos, error, cargando } = useDatos(() => api.get('/portafolio/matriz'))
  if (cargando) return <Pagina titulo="Portafolios"><Cargando /></Pagina>
  if (error) return <Pagina titulo="Portafolios"><Aviso tono="grave">{error}</Aviso></Pagina>
  const tono = { publicada: 'bg-petroleo-suave text-petroleo-oscuro', aprobada: 'bg-aviso-suave text-aviso', preliminar: 'bg-aviso-suave text-aviso', error: 'bg-grave-suave text-grave' }
  return (
    <Pagina titulo="Portafolios" bajada="Entregas de cada estudiante en los laboratorios de los dos cortes. Abre una celda para ver la evaluación.">
      {datos.filas.length === 0 ? <Vacio titulo="Aún no hay estudiantes">Los estudiantes aparecen aquí cuando crean su cuenta o cuando los registras en Administración.</Vacio> : (
        <div className="overflow-x-auto rounded-xl border border-linea bg-white">
          <table className="tabla w-full">
            <thead>
              <tr>
                <th>Estudiante</th>
                {datos.laboratorios.map((l) => <th key={l.id} title={l.titulo} className="text-center"><Link to={`/app/laboratorios/${l.id}`} className="hover:underline">{l.etiqueta}</Link></th>)}
              </tr>
            </thead>
            <tbody>
              {datos.filas.map((f) => (
                <tr key={f.estudiante.id}>
                  <td><Link to={`/app/portafolio/${f.estudiante.id}`} className="font-medium hover:underline">{f.estudiante.nombre}</Link>{f.estudiante.codigo && <span className="block text-sm text-grafito">{f.estudiante.codigo}</span>}</td>
                  {datos.laboratorios.map((l) => {
                    const c = f.celdas[l.id]
                    if (!c) return <td key={l.id} className="text-center text-grafito" title="Sin entrega">·</td>
                    const destino = c.evaluacion_id ? `/app/evaluaciones/${c.evaluacion_id}` : `/app/laboratorios/${l.id}`
                    return <td key={l.id} className="text-center">
                      <Link to={destino} title={ESTADOS[c.estado]?.texto} className={`num inline-block min-w-[3.2rem] rounded-md px-2 py-1 font-medium hover:underline ${tono[c.estado] || 'bg-dom-0 text-grafito'}`}>
                        {c.nota != null ? fmtNota(c.nota) : c.estado === 'error' ? 'error' : 'sin ev.'}
                      </Link>
                    </td>
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="border-t border-linea px-4 py-2.5 text-sm text-grafito">
            <span className="mr-4"><span className="mr-1 inline-block h-3 w-3 rounded-sm bg-petroleo-suave align-middle" /> publicada</span>
            <span className="mr-4"><span className="mr-1 inline-block h-3 w-3 rounded-sm bg-aviso-suave align-middle" /> preliminar o aprobada, sin publicar</span>
            <span>· sin entrega</span>
          </p>
        </div>
      )}
    </Pagina>
  )
}

export default function Portafolio() {
  const { esDocente } = useAuth()
  const { estudianteId } = useParams()
  if (esDocente && !estudianteId) return <Matriz />
  return <PortafolioEstudiante estudianteId={esDocente ? estudianteId : null} />
}
