import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { FilePlus2, Pencil, Play, RefreshCw, Trash2, Upload } from 'lucide-react'
import { api, estadoOculto, fmtFecha, fmtFechaHora, fmtNota } from '../api'
import { useAuth } from '../auth.jsx'
import { Aviso, Boton, Campo, Cargando, Estado, Modal, Pagina, Pestanas, Seccion, Vacio, useDatos } from '../ui.jsx'
import { FormularioLab } from './Laboratorios.jsx'
import { Evidencias } from './Portafolio.jsx'

export function TablaRubrica({ rubrica }) {
  const comp = Object.fromEntries(rubrica.competencias.map((c) => [c.id, c.nombre]))
  return (
    <div className="overflow-x-auto">
      <table className="tabla w-full min-w-[720px] text-[0.93rem]">
        <thead>
          <tr><th>Criterio</th><th className="text-right">Peso</th>{rubrica.niveles.map((n) => <th key={n.id}>{n.nombre} <span className="num font-normal">({fmtNota(n.puntaje)})</span></th>)}</tr>
        </thead>
        <tbody>
          {rubrica.criterios.map((c) => (
            <tr key={c.id}>
              <td className="min-w-[11rem]"><span className="font-medium">{c.nombre}</span><span className="block text-sm text-grafito">{comp[c.competencia_id]}</span>
                {c.regla && <span className="mt-1 block text-sm text-petroleo-oscuro">Regla objetiva: si falla {{ sintaxis: 'la sintaxis', analisis_estatico: 'el análisis estático', pruebas: 'las pruebas' }[c.regla.verificacion]}, máximo «{rubrica.niveles.find((n) => n.id === c.regla.nivel_tope)?.nombre}»</span>}</td>
              <td className="num text-right font-medium">{c.ponderacion} %</td>
              {rubrica.niveles.map((n) => <td key={n.id} className="text-grafito">{c.descriptores[n.id] || '—'}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function FormularioEntrega({ labId, estudiantes, onHecho }) {
  const [f, setF] = useState({ repo_url: '', video_url: '', presentacion_url: '', comentario: '', estudiante_id: '' })
  const [modoCodigo, setModoCodigo] = useState('zip')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const refs = { informe: useRef(null), codigo: useRef(null), presentacion: useRef(null) }
  const cambiar = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const enviar = async (e) => {
    e.preventDefault(); setError('')
    const fd = new FormData()
    const informe = refs.informe.current.files[0]
    if (!informe) return setError('Adjunta el informe en PDF.')
    fd.append('informe', informe)
    if (modoCodigo === 'zip') {
      const zip = refs.codigo.current?.files[0]
      if (!zip) return setError('Adjunta el ZIP con el código o cambia a repositorio de GitHub.')
      fd.append('codigo', zip)
    } else if (!f.repo_url.trim()) return setError('Escribe la URL del repositorio de GitHub.')
    else fd.append('repo_url', f.repo_url.trim())
    const pres = refs.presentacion.current?.files[0]
    if (pres) fd.append('presentacion', pres)
    for (const k of ['video_url', 'presentacion_url', 'comentario', 'estudiante_id']) if (f[k]) fd.append(k, f[k])
    setOcupado(true)
    const formulario = e.currentTarget
    try {
      const r = await api.post(`/laboratorios/${labId}/entregas`, fd)
      formulario.reset(); setF((a) => ({ ...a, repo_url: '', video_url: '', presentacion_url: '', comentario: '' }))
      onHecho(r)
    }
    catch (err) { setError(err.message) } finally { setOcupado(false) }
  }
  return (
    <form onSubmit={enviar} className="space-y-4">
      {estudiantes && <Campo etiqueta="Estudiante"><select className="campo" required value={f.estudiante_id} onChange={cambiar('estudiante_id')}>
        <option value="">Selecciona…</option>{estudiantes.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}</select></Campo>}
      <Campo etiqueta="Informe (PDF con texto legible)" ayuda="No uses un PDF escaneado: la IA necesita poder citar el texto.">
        <input ref={refs.informe} type="file" accept="application/pdf,.pdf" className="campo" /></Campo>
      <fieldset>
        <legend className="mb-1 text-sm font-medium">Código fuente</legend>
        <div className="mb-2 flex gap-4">
          {[['zip', 'Archivo ZIP'], ['repo', 'Repositorio público de GitHub']].map(([v, t]) => (
            <label key={v} className="flex items-center gap-2"><input type="radio" name="modo" checked={modoCodigo === v} onChange={() => setModoCodigo(v)} className="accent-petroleo" />{t}</label>))}
        </div>
        {modoCodigo === 'zip'
          ? <input ref={refs.codigo} type="file" accept=".zip,application/zip" className="campo" aria-label="Archivo ZIP con el código" />
          : <input className="campo" type="url" placeholder="https://github.com/usuario/repositorio" value={f.repo_url} onChange={cambiar('repo_url')} aria-label="URL del repositorio" />}
        <span className="mt-1 block text-sm text-grafito">Si incluyes pruebas (archivos test_*.py) se ejecutan en un entorno aislado y cuentan como evidencia.</span>
      </fieldset>
      <details className="rounded-lg border border-linea px-3.5 py-2.5">
        <summary className="cursor-pointer font-medium">Video y presentación (opcionales)</summary>
        <div className="mt-3 space-y-3">
          <Campo etiqueta="Enlace del video"><input className="campo" type="url" placeholder="https://…" value={f.video_url} onChange={cambiar('video_url')} /></Campo>
          <Campo etiqueta="Presentación (PPTX o PDF)"><input ref={refs.presentacion} type="file" accept=".pptx,.pdf" className="campo" /></Campo>
          <Campo etiqueta="O enlace de la presentación"><input className="campo" type="url" placeholder="https://…" value={f.presentacion_url} onChange={cambiar('presentacion_url')} /></Campo>
        </div>
      </details>
      <Campo etiqueta="Comentario para el docente (opcional)"><textarea className="campo" value={f.comentario} onChange={cambiar('comentario')} /></Campo>
      {error && <Aviso tono="grave">{error}</Aviso>}
      <Boton type="submit" icono={Upload} ocupado={ocupado}>Enviar entrega</Boton>
    </form>
  )
}

function TarjetaEntrega({ e, lab, onCambio }) {
  const { esDocente } = useAuth()
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const ultima = e.evaluaciones.at(-1)
  const enCurso = ultima && ['en_cola', 'procesando'].includes(ultima.estado)
  const revisada = e.evaluaciones.some((x) => ['aprobada', 'publicada'].includes(x.estado))
  const evaluar = async (forzar) => {
    setOcupado(true); setError('')
    try { await api.post(`/entregas/${e.id}/evaluar`, { forzar }); await onCambio() } catch (err) { setError(err.message) } finally { setOcupado(false) }
  }
  const borrar = async () => {
    if (!window.confirm('¿Eliminar esta entrega y sus evaluaciones?')) return
    try { await api.del(`/entregas/${e.id}`); await onCambio() } catch (err) { setError(err.message) }
  }
  return (
    <article className="rounded-xl border border-linea bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          {esDocente && <p className="font-medium"><Link to={`/app/portafolio/${e.estudiante.id}`} className="hover:underline">{e.estudiante.nombre}</Link></p>}
          <p className="text-sm text-grafito">Entrega {e.numero} · {fmtFechaHora(e.creado_en)}{e.rubrica_version && ` · rúbrica v${e.rubrica_version.version}`}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!enCurso && lab.rubrica && (!revisada || esDocente) && (
            <Boton icono={ultima ? RefreshCw : Play} variante={ultima ? 'secundario' : 'primario'} ocupado={ocupado} onClick={() => evaluar(Boolean(ultima) && esDocente)}>
              {ultima ? 'Evaluar de nuevo' : 'Evaluar con IA'}
            </Boton>)}
          {(!revisada || esDocente) && !enCurso && <Boton variante="fantasma" icono={Trash2} onClick={borrar} aria-label="Eliminar entrega" />}
        </div>
      </div>
      <div className="mt-3"><Evidencias e={e} /></div>
      {e.comentario && <p className="mt-2 text-[0.95rem] text-grafito">«{e.comentario}»</p>}
      {error && <div className="mt-3"><Aviso tono="grave">{error}</Aviso></div>}
      {!lab.rubrica && <div className="mt-3"><Aviso tono="aviso">Este laboratorio aún no tiene una rúbrica validada, así que no se puede evaluar todavía.</Aviso></div>}
      {e.evaluaciones.length > 0 && (
        <ul className="mt-3 divide-y divide-linea border-t border-linea">
          {[...e.evaluaciones].reverse().map((ev) => (
            <li key={ev.id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-2.5">
              <span className="flex flex-wrap items-center gap-2">
                <Estado valor={ev.visible ? ev.estado : estadoOculto(ev.estado)} />
                {['en_cola', 'procesando'].includes(ev.estado) && <span className="text-sm text-grafito">{ev.progreso}</span>}
                {!ev.visible && ['preliminar', 'aprobada'].includes(ev.estado) && <span className="text-sm text-grafito">Lista. Tu docente la está revisando antes de publicarla.</span>}
                {ev.estado === 'error' && <span className="text-sm text-grave">{ev.error}</span>}
              </span>
              <span className="flex items-center gap-4">
                <span className="text-sm text-grafito">{ev.modelo}</span>
                {ev.visible && ev.nota != null && <span className="num titulo text-lg font-bold">{fmtNota(ev.nota)}</span>}
                {ev.visible && !['en_cola', 'procesando', 'error'].includes(ev.estado) && <Link to={`/app/evaluaciones/${ev.id}`} className="font-medium text-petroleo underline">{esDocente && ev.estado !== 'publicada' ? 'Revisar' : 'Ver'}</Link>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}

function Rubricas({ lab }) {
  const navegar = useNavigate()
  const archivo = useRef(null)
  const [ocupado, setOcupado] = useState('')
  const [error, setError] = useState('')
  const hacer = async (clave, fn) => {
    setOcupado(clave); setError('')
    try { const rv = await fn(); navegar(`/app/rubricas/${rv.id}`) } catch (e) { setError(e.message); setOcupado('') }
  }
  const subir = (e) => {
    const f = e.target.files[0]
    if (!f) return
    const fd = new FormData(); fd.append('archivo', f)
    hacer('archivo', () => api.post(`/laboratorios/${lab.id}/rubricas/archivo`, fd))
  }
  return (
    <div className="space-y-5">
      <Seccion titulo="Cargar o crear una rúbrica">
        <p className="max-w-3xl text-grafito">Sube el archivo de la rúbrica (PDF, Word, Excel, CSV, Markdown o JSON). La plataforma identifica competencias, criterios, descriptores, niveles y ponderaciones, y te muestra las inconsistencias para corregirlas antes de evaluar.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <input ref={archivo} type="file" className="hidden" accept=".pdf,.docx,.xlsx,.csv,.tsv,.md,.txt,.json" onChange={subir} />
          <Boton icono={Upload} ocupado={ocupado === 'archivo'} onClick={() => archivo.current.click()}>Cargar archivo de rúbrica</Boton>
          <Boton variante="secundario" icono={FilePlus2} ocupado={ocupado === 'plantilla'} onClick={() => hacer('plantilla', () => api.post(`/laboratorios/${lab.id}/rubricas`, {}))}>Empezar con una plantilla</Boton>
        </div>
        {ocupado === 'archivo' && <p className="mt-3 text-grafito">Interpretando la rúbrica. Con un modelo de IA puede tardar unos segundos.</p>}
        {error && <div className="mt-3"><Aviso tono="grave">{error}</Aviso></div>}
      </Seccion>
      <Seccion titulo="Versiones">
        {lab.rubricas.length === 0 ? <p className="text-grafito">Aún no hay versiones.</p> : (
          <div className="overflow-x-auto">
            <table className="tabla w-full">
              <thead><tr><th>Versión</th><th>Estado</th><th>Origen</th><th>Criterios</th><th>Inconsistencias</th><th></th></tr></thead>
              <tbody>
                {[...lab.rubricas].reverse().map((r) => (
                  <tr key={r.id}>
                    <td className="num font-medium">v{r.version}{lab.rubrica?.id === r.id && <span className="ml-2 rounded-full bg-petroleo-suave px-2 py-0.5 text-sm text-petroleo-oscuro">vigente</span>}</td>
                    <td>{r.estado === 'validada' ? `Validada el ${fmtFecha(r.validada_en)}` : 'Borrador'}</td>
                    <td className="text-grafito">{r.origen}{r.archivo && <span className="block text-sm">{r.archivo.nombre}</span>}{r.interpretada_por && <span className="block text-sm">{r.interpretada_por}</span>}</td>
                    <td className="num">{r.criterios}</td>
                    <td>{r.errores ? <span className="font-medium text-grave">{r.errores} por corregir</span> : 'Sin errores'}{r.advertencias > 0 && <span className="block text-sm text-aviso">{r.advertencias} advertencias</span>}</td>
                    <td className="whitespace-nowrap text-right">
                      {r.estado === 'borrador'
                        ? <Link to={`/app/rubricas/${r.id}`} className="font-medium text-petroleo underline">Corregir y validar</Link>
                        : <><Link to={`/app/rubricas/${r.id}`} className="mr-4 font-medium text-petroleo underline">Ver</Link>
                          <button className="font-medium text-petroleo underline" onClick={() => hacer('copia', () => api.post(`/laboratorios/${lab.id}/rubricas`, { desde_version: r.id }))}>Nueva versión</button></>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>)}
        <p className="mt-3 text-sm text-grafito">Una versión validada no se modifica: cada evaluación conserva la versión exacta con la que se calculó.</p>
      </Seccion>
    </div>
  )
}

export default function Laboratorio() {
  const { id } = useParams()
  const { esDocente } = useAuth()
  const navegar = useNavigate()
  const { datos, error, cargando, recargar } = useDatos(async () => {
    const [lab, entregas, cohortes, estudiantes] = await Promise.all([
      api.get(`/laboratorios/${id}`), api.get(`/entregas?laboratorio_id=${id}`),
      esDocente ? api.get('/cohortes') : null, esDocente ? api.get('/usuarios?rol=estudiante') : null])
    return { lab, entregas, cohortes, estudiantes }
  }, [id])
  const [elegida, setPestana] = useState(null)
  const [modal, setModal] = useState(null)
  const [errorAccion, setErrorAccion] = useState('')

  const enCurso = datos?.entregas.some((e) => e.evaluaciones.some((x) => ['en_cola', 'procesando'].includes(x.estado)))
  useEffect(() => {
    if (!enCurso) return
    const t = setInterval(() => recargar(true), 2500)
    return () => clearInterval(t)
  }, [enCurso, recargar])

  if (cargando) return <Pagina titulo="Laboratorio"><Cargando /></Pagina>
  if (error) return <Pagina titulo="Laboratorio"><Aviso tono="grave">{error}</Aviso></Pagina>
  const { lab, entregas } = datos
  // Sin rúbrica validada, lo primero que necesita el docente es cargarla.
  const pestana = elegida || (esDocente ? (lab.rubrica ? 'entregas' : 'rubrica') : 'entrega')
  const pendientes = entregas.filter((e) => e.evaluaciones.length === 0)
  const evaluarPendientes = async () => {
    setErrorAccion('')
    try { for (const e of pendientes) await api.post(`/entregas/${e.id}/evaluar`, {}); await recargar(true) } catch (e) { setErrorAccion(e.message); recargar(true) }
  }
  const borrarLab = async () => {
    if (!window.confirm('¿Eliminar este laboratorio?')) return
    try { await api.del(`/laboratorios/${id}`); navegar('/app/laboratorios') } catch (e) { setErrorAccion(e.message) }
  }
  const pestanas = esDocente
    ? [['entregas', 'Entregas', entregas.filter((e) => e.evaluaciones.some((x) => x.estado === 'preliminar')).length], ['rubrica', 'Rúbrica'], ['enunciado', 'Enunciado']]
    : [['entrega', 'Mi entrega'], ['enunciado', 'Enunciado'], ['rubrica', 'Rúbrica']]
  return (
    <Pagina titulo={lab.titulo}
      migas={<Link to={esDocente ? '/app/laboratorios' : '/app/portafolio'} className="underline">{esDocente ? 'Laboratorios y rúbricas' : 'Mi portafolio'}</Link>}
      bajada={`${lab.cohorte} · laboratorio ${lab.orden}${lab.fecha ? ` · ${fmtFecha(lab.fecha)}` : ''}`}
      acciones={esDocente && <><Boton variante="secundario" icono={Pencil} onClick={() => setModal('editar')}>Editar</Boton><Boton variante="fantasma" icono={Trash2} onClick={borrarLab} aria-label="Eliminar laboratorio" /></>}>
      {errorAccion && <div className="mb-4"><Aviso tono="grave">{errorAccion}</Aviso></div>}
      {esDocente && !lab.rubrica && <div className="mb-5"><Aviso tono="aviso" titulo="Falta validar la rúbrica">Carga la rúbrica y corrige sus inconsistencias en la pestaña Rúbrica. Hasta entonces no se pueden evaluar entregas.</Aviso></div>}
      <Pestanas opciones={pestanas} valor={pestana} onCambio={setPestana} />

      {pestana === 'enunciado' && (
        <div className="grid gap-5 lg:grid-cols-2">
          <Seccion titulo="Descripción"><p className="whitespace-pre-line">{lab.descripcion || 'Sin descripción.'}</p></Seccion>
          <Seccion titulo="Objetivos"><p className="whitespace-pre-line">{lab.objetivos || 'Sin objetivos.'}</p></Seccion>
          {esDocente && lab.pruebas_docente && <Seccion titulo="Pruebas del docente" className="lg:col-span-2"><pre className="fuente">{lab.pruebas_docente}</pre></Seccion>}
        </div>
      )}

      {pestana === 'rubrica' && (esDocente ? <Rubricas lab={lab} /> : (
        lab.rubrica_vigente
          ? <Seccion titulo={lab.rubrica_vigente.titulo || 'Rúbrica'} extra={<span className="text-sm text-grafito">Versión {lab.rubrica_vigente.version}</span>}><TablaRubrica rubrica={lab.rubrica_vigente.contenido} /></Seccion>
          : <Vacio titulo="La rúbrica aún no está publicada">Tu docente la está preparando.</Vacio>))}

      {pestana === 'entrega' && (
        <div className="space-y-5">
          {entregas.map((e) => <TarjetaEntrega key={e.id} e={e} lab={lab} onCambio={() => recargar(true)} />)}
          <Seccion titulo={entregas.length ? 'Subir una nueva versión de tu entrega' : 'Entrega tu laboratorio'}>
            <FormularioEntrega labId={id} onHecho={() => recargar(true)} />
          </Seccion>
        </div>
      )}

      {pestana === 'entregas' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-grafito">{entregas.length} {entregas.length === 1 ? 'entrega' : 'entregas'}{pendientes.length > 0 && ` · ${pendientes.length} sin evaluar`}</p>
            <div className="flex gap-2">
              {pendientes.length > 0 && lab.rubrica && <Boton icono={Play} onClick={evaluarPendientes}>Evaluar las {pendientes.length} pendientes</Boton>}
              <Boton variante="secundario" icono={Upload} onClick={() => setModal('entrega')}>Cargar entrega de un estudiante</Boton>
            </div>
          </div>
          {entregas.length === 0 && <Vacio titulo="Todavía no hay entregas">Los estudiantes las suben desde su portafolio; también puedes cargarlas tú.</Vacio>}
          {entregas.map((e) => <TarjetaEntrega key={e.id} e={e} lab={lab} onCambio={() => recargar(true)} />)}
        </div>
      )}

      {modal === 'editar' && (
        <Modal titulo="Editar laboratorio" onCerrar={() => setModal(null)}>
          <FormularioLab inicial={{ cohorte_id: lab.cohorte_id, orden: lab.orden, titulo: lab.titulo, descripcion: lab.descripcion, objetivos: lab.objetivos, fecha: lab.fecha || '', pruebas_docente: lab.pruebas_docente || '' }}
            cohortes={datos.cohortes} onCancelar={() => setModal(null)}
            onGuardar={async (f) => { await api.patch(`/laboratorios/${id}`, f); setModal(null); recargar(true) }} />
        </Modal>)}
      {modal === 'entrega' && (
        <Modal titulo="Cargar entrega de un estudiante" onCerrar={() => setModal(null)}>
          <FormularioEntrega labId={id} estudiantes={datos.estudiantes} onHecho={() => { setModal(null); recargar(true) }} />
        </Modal>)}
    </Pagina>
  )
}
