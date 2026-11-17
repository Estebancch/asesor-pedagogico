import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { BadgeCheck, CircleAlert, Pencil, RotateCcw, Send, ShieldCheck, TriangleAlert } from 'lucide-react'
import { api, fmtAccion, fmtFechaHora, fmtNota, fmtNum } from '../api'
import { useAuth } from '../auth.jsx'
import { Aviso, Boton, Campo, Cargando, Dominio, Estado, Lista, Modal, Pagina, Pestanas, Regla, Seccion, useDatos } from '../ui.jsx'
import { Evidencias } from './Portafolio.jsx'

const escapar = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

function VisorFuente({ evaluacionId, cita, onCerrar }) {
  const { datos, error, cargando } = useDatos(() => api.get(`/evaluaciones/${evaluacionId}/fuente?id=${encodeURIComponent(cita.fuente)}`))
  const marca = useRef(null)
  const partes = useMemo(() => {
    if (!datos) return null
    const palabras = cita.cita.trim().split(/\s+/)
    for (const n of [palabras.length, 8, 5]) {
      if (n > palabras.length) continue
      const m = new RegExp(palabras.slice(0, n).map(escapar).join('\\s+'), 'i').exec(datos.texto)
      if (m) return [datos.texto.slice(0, m.index), m[0], datos.texto.slice(m.index + m[0].length)]
    }
    return [datos.texto, '', '']
  }, [datos, cita])
  useEffect(() => { marca.current?.scrollIntoView({ block: 'center' }) }, [partes])
  return (
    <Modal titulo={datos?.titulo || cita.fuente} onCerrar={onCerrar} ancho="max-w-4xl">
      {cargando && <Cargando />}
      {error && <Aviso tono="grave">{error}</Aviso>}
      {partes && <>
        <p className="mb-3 text-sm text-grafito">Texto de la fuente tal como se analizó. {partes[1] ? 'El fragmento citado aparece resaltado.' : 'El fragmento citado no se encontró literalmente en esta fuente.'}</p>
        <pre className="fuente max-h-[62vh] overflow-auto rounded-lg border border-linea bg-papel p-4">{partes[0]}{partes[1] && <mark ref={marca} className="cita">{partes[1]}</mark>}{partes[2]}</pre>
      </>}
    </Modal>
  )
}

function Cita({ e, onVer }) {
  const verificada = e.estado === 'verificada', parcial = e.estado === 'parcial'
  return (
    <blockquote className="border-l-2 border-tinta/20 pl-3.5">
      <p className="text-[0.97rem] leading-relaxed">«<span className={verificada || parcial ? 'cita' : 'cita-dudosa'}>{e.cita}</span>»</p>
      <footer className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm text-grafito">
        <button onClick={() => onVer(e)} className="text-petroleo underline">{e.fuente.replace(/^codigo:/, '').replace(/^informe:p/, 'informe, página ').replace(/^presentacion:d/, 'presentación, diapositiva ').replace('verificacion:resumen', 'verificación técnica')}{e.linea && e.fuente.startsWith('codigo:') ? `, línea ${e.linea}` : ''}</button>
        {verificada && <span className="inline-flex items-center gap-1 text-petroleo-oscuro"><BadgeCheck size={15} aria-hidden />Cita verificada</span>}
        {parcial && <span className="inline-flex items-center gap-1 text-aviso"><TriangleAlert size={15} aria-hidden />Coincide solo en parte</span>}
        {!verificada && !parcial && <span className="inline-flex items-center gap-1 text-grave"><CircleAlert size={15} aria-hidden />No se encontró en la entrega</span>}
      </footer>
      {e.explicacion && <p className="mt-1 text-[0.95rem] text-grafito">{e.explicacion}</p>}
    </blockquote>
  )
}

function ModalAjuste({ evaluacion, criterio, rubrica, onCerrar, onGuardado }) {
  const [f, setF] = useState({ nivel_id: criterio.nivel_id || '', manual: criterio.puntaje_manual ?? '', justificacion: criterio.justificacion, recomendaciones: criterio.recomendaciones.join('\n'), comentario: '' })
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const cambiaValor = f.nivel_id !== (criterio.nivel_id || '') || String(f.manual) !== String(criterio.puntaje_manual ?? '')
  const enviar = async (e) => {
    e.preventDefault(); setOcupado(true); setError('')
    const cuerpo = { justificacion: f.justificacion, recomendaciones: f.recomendaciones.split('\n'), comentario: f.comentario }
    if (f.nivel_id !== (criterio.nivel_id || '')) cuerpo.nivel_id = f.nivel_id
    if (f.manual === '' && criterio.puntaje_manual != null) cuerpo.quitar_puntaje_manual = true
    else if (f.manual !== '' && Number(f.manual) !== criterio.puntaje_manual) cuerpo.puntaje_manual = Number(f.manual)
    try { onGuardado(await api.patch(`/evaluaciones/${evaluacion.id}/criterios/${criterio.criterio_id}`, cuerpo)) }
    catch (err) { setError(err.message); setOcupado(false) }
  }
  const nivelIA = rubrica.niveles.find((n) => n.id === criterio.nivel_ia)
  return (
    <Modal titulo={`Ajustar: ${criterio.nombre}`} onCerrar={onCerrar}>
      <form onSubmit={enviar} className="space-y-4">
        <p className="text-grafito">La IA propuso «{nivelIA?.nombre || 'sin nivel'}». Al cambiar el nivel, el servidor recalcula la nota con las ponderaciones de la rúbrica.</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <Campo etiqueta="Nivel de desempeño">
            <select className="campo" value={f.nivel_id} onChange={(e) => setF({ ...f, nivel_id: e.target.value, manual: '' })}>
              <option value="" disabled>Selecciona…</option>
              {rubrica.niveles.map((n) => <option key={n.id} value={n.id}>{n.nombre} ({fmtNota(n.puntaje)})</option>)}
            </select>
          </Campo>
          <Campo etiqueta="Puntaje exacto (opcional)" ayuda="Solo si necesitas un valor intermedio entre niveles.">
            <input className="campo num" type="number" min="0" max="5" step="0.1" value={f.manual} onChange={(e) => setF({ ...f, manual: e.target.value })} />
          </Campo>
        </div>
        <Campo etiqueta="Justificación que verá el estudiante"><textarea className="campo min-h-[7rem]" value={f.justificacion} onChange={(e) => setF({ ...f, justificacion: e.target.value })} /></Campo>
        <Campo etiqueta="Recomendaciones" ayuda="Una por línea."><textarea className="campo" value={f.recomendaciones} onChange={(e) => setF({ ...f, recomendaciones: e.target.value })} /></Campo>
        <Campo etiqueta={`Motivo del ajuste${cambiaValor ? '' : ' (opcional)'}`} ayuda="Queda en el registro de auditoría; el estudiante no lo ve.">
          <input className="campo" required={cambiaValor} value={f.comentario} onChange={(e) => setF({ ...f, comentario: e.target.value })} />
        </Campo>
        {error && <Aviso tono="grave">{error}</Aviso>}
        <div className="flex justify-end gap-2"><Boton type="button" variante="secundario" onClick={onCerrar}>Cancelar</Boton><Boton type="submit" ocupado={ocupado}>Guardar ajuste</Boton></div>
      </form>
    </Modal>
  )
}

function Criterio({ c, rubrica, editable, onAjustar, onVer }) {
  const niveles = [...rubrica.niveles].sort((a, b) => b.puntaje - a.puntaje)
  const comp = rubrica.competencias.find((k) => k.id === c.competencia_id)
  return (
    <article className="rounded-xl border border-linea bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-lg font-bold">{c.nombre}</h3>
          <p className="text-sm text-grafito">{comp?.nombre} · pesa {c.ponderacion} % de la nota{c.confianza && ` · confianza de la IA: ${c.confianza}`}</p>
        </div>
        {editable && <Boton variante="secundario" icono={Pencil} onClick={() => onAjustar(c)}>Ajustar</Boton>}
      </div>
      <ol className="mt-3 flex flex-wrap gap-1.5" aria-label="Nivel asignado">
        {niveles.map((n) => {
          const activo = n.id === c.nivel_id, deIA = n.id === c.nivel_ia && !activo
          return <li key={n.id} className={`rounded-md px-2.5 py-1 text-sm ${activo ? 'bg-tinta font-medium text-white' : deIA ? 'border border-dashed border-grafito text-grafito' : 'border border-linea text-grafito'}`}
            title={deIA ? 'Nivel propuesto por la IA' : undefined}>{n.nombre} <span className="num">{fmtNota(n.puntaje)}</span>{activo && <span className="sr-only"> (asignado)</span>}{deIA && ' · propuesta de la IA'}</li>
        })}
        {c.puntaje_manual != null && <li className="rounded-md bg-petroleo px-2.5 py-1 text-sm font-medium text-white">Puntaje del docente: <span className="num">{fmtNota(c.puntaje_manual)}</span></li>}
      </ol>
      {c.nivel_id && c.descriptores_nivel && <p className="mt-2 text-sm text-grafito">{c.descriptores_nivel}</p>}
      {c.ajuste_regla && <div className="mt-3"><Aviso tono="aviso" titulo="Regla objetiva de la rúbrica aplicada">{c.ajuste_regla.motivo}</Aviso></div>}
      {c.ajuste_docente && <p className="mt-3 flex items-center gap-1.5 text-sm text-petroleo-oscuro"><ShieldCheck size={16} aria-hidden />Ajustada por {c.ajuste_docente.por} el {fmtFechaHora(c.ajuste_docente.en)}</p>}
      {editable && c.alertas.length > 0 && <ul className="mt-3 space-y-1">{c.alertas.map((a, i) => <li key={i} className="flex gap-2 text-[0.95rem] text-aviso"><TriangleAlert size={17} className="mt-0.5 shrink-0" aria-hidden />{a}</li>)}</ul>}
      <p className="mt-4 max-w-[75ch]">{c.justificacion || 'Sin justificación.'}</p>
      {c.evidencias.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-sm font-medium">Evidencia citada</p>
          <div className="space-y-3">{c.evidencias.map((e, i) => <Cita key={i} e={e} onVer={onVer} />)}</div>
        </div>)}
      <div className="mt-5 grid gap-5 border-t border-linea pt-4 md:grid-cols-3">
        <div><p className="mb-1.5 text-sm font-medium">Fortalezas</p><Lista items={c.fortalezas} vacio="—" /></div>
        <div><p className="mb-1.5 text-sm font-medium">Por mejorar</p><Lista items={c.debilidades} vacio="—" /></div>
        <div><p className="mb-1.5 text-sm font-medium">Recomendaciones</p><Lista items={c.recomendaciones} vacio="—" /></div>
      </div>
    </article>
  )
}

function Verificacion({ v }) {
  const s = v.sintaxis || {}, a = v.analisis_estatico || {}, p = v.pruebas || {}, sb = v.sandbox || {}
  const TXT = { ok: 'Correcto', falla: 'Con fallas', no_aplica: 'No aplica', advertencias: 'Con advertencias', sin_pruebas: 'Sin pruebas', error: 'No terminó', deshabilitado: 'Deshabilitado', no_ejecutable: 'No ejecutable en el sandbox' }
  const tono = (e) => (e === 'ok' ? 'text-petroleo-oscuro' : ['falla', 'error'].includes(e) ? 'text-grave' : 'text-aviso')
  const capas = [['directorio_aislado', 'Copia aislada de la entrega'], ['entorno_limpio', 'Sin variables del servidor'], ['rlimits', 'Límites de CPU, memoria y procesos'], ['seccomp', 'Sin sockets (seccomp, kernel)'], ['audit_hook', 'Sin red, subprocesos ni archivos ajenos (audit hook)'], ['usuario_sin_privilegios', 'Usuario sin privilegios']]
  return (
    <div className="space-y-5">
      {(v.notas || []).map((n, i) => <Aviso key={i} tono="aviso">{n}</Aviso>)}
      <div className="grid gap-5 lg:grid-cols-3">
        <Seccion titulo="Sintaxis"><p className={`titulo text-xl font-bold ${tono(s.estado)}`}>{TXT[s.estado] || s.estado}</p><p className="text-grafito">{s.archivos_revisados || 0} archivos revisados</p>
          <ul className="mt-2 space-y-1.5 text-[0.95rem]">{(s.errores || []).map((e, i) => <li key={i}><span className="font-medium">{e.archivo}:{e.linea}</span> {e.mensaje}{e.texto && <code className="mt-0.5 block rounded bg-papel px-2 py-1 text-sm">{e.texto}</code>}</li>)}</ul></Seccion>
        <Seccion titulo="Análisis estático"><p className={`titulo text-xl font-bold ${tono(a.estado)}`}>{TXT[a.estado] || a.estado}</p>
          {a.metricas && Object.keys(a.metricas).length > 0 && <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-3 gap-y-0.5 text-[0.95rem]">
            {[['Archivos Python', a.metricas.archivos_python], ['Notebooks', a.metricas.notebooks], ['Líneas de código', a.metricas.lineas_codigo], ['Funciones', a.metricas.funciones], ['Clases', a.metricas.clases], ['Con docstring', a.metricas.con_docstring], ['Complejidad máxima', a.metricas.complejidad_max]].map(([k, val]) => <div key={k} className="contents"><dt className="text-grafito">{k}</dt><dd className="num text-right">{val}</dd></div>)}</dl>}</Seccion>
        <Seccion titulo="Pruebas unitarias"><p className={`titulo text-xl font-bold ${tono(p.estado)}`}>{TXT[p.estado] || p.estado}</p>
          <p className="num text-grafito">{p.aprobadas || 0} de {p.total || 0} aprobadas{p.fallidas ? ` · ${p.fallidas} fallidas` : ''}{p.errores ? ` · ${p.errores} con error` : ''}</p>
          <p className="mt-1 text-sm text-grafito">{p.origen?.estudiante || 0} {p.origen?.estudiante === 1 ? 'archivo' : 'archivos'} de prueba del estudiante{p.origen?.docente ? ' · con pruebas del docente' : ''}{p.duracion_s ? ` · ${fmtNum(p.duracion_s)} s` : ''}</p></Seccion>
      </div>
      {(a.hallazgos?.length > 0 || a.seguridad?.length > 0) && (
        <Seccion titulo="Hallazgos del análisis estático">
          <div className="overflow-x-auto"><table className="tabla w-full text-[0.95rem]"><thead><tr><th>Tipo</th><th>Ubicación</th><th>Detalle</th></tr></thead><tbody>
            {(a.seguridad || []).map((h, i) => <tr key={`s${i}`}><td className="font-medium text-grave">Riesgo</td><td className="num whitespace-nowrap">{h.archivo}:{h.linea}</td><td>{h.mensaje}</td></tr>)}
            {(a.hallazgos || []).map((h, i) => <tr key={i}><td className={h.tipo === 'error' ? 'font-medium text-grave' : 'text-aviso'}>{h.tipo === 'error' ? 'Error' : 'Advertencia'}</td><td className="num whitespace-nowrap">{h.archivo}:{h.linea}</td><td>{h.mensaje}</td></tr>)}
          </tbody></table></div>
        </Seccion>)}
      {p.detalle?.length > 0 && (
        <Seccion titulo="Resultado de cada prueba">
          <div className="overflow-x-auto"><table className="tabla w-full text-[0.95rem]"><thead><tr><th>Prueba</th><th>Resultado</th><th>Mensaje</th></tr></thead><tbody>
            {p.detalle.map((d, i) => <tr key={i}><td className="break-all">{d.nombre}</td><td className={d.resultado === 'aprobada' ? 'text-petroleo-oscuro' : 'font-medium text-grave'}>{d.resultado}</td><td className="text-grafito">{d.mensaje}</td></tr>)}
          </tbody></table></div>
          {p.salida && <details className="mt-3"><summary className="cursor-pointer font-medium text-petroleo">Salida completa de pytest</summary><pre className="fuente mt-2 max-h-80 overflow-auto rounded-lg bg-papel p-3">{p.salida}</pre></details>}
        </Seccion>)}
      <Seccion titulo="Entorno aislado en el que se ejecutó">
        <div className="grid gap-5 md:grid-cols-2">
          <ul className="space-y-1.5">{capas.map(([k, t]) => <li key={k} className="flex items-center gap-2">{sb.capas?.[k] ? <BadgeCheck size={17} className="text-petroleo" aria-label="Activa" /> : <CircleAlert size={17} className="text-aviso" aria-label="No activa" />}{t}</li>)}</ul>
          {sb.limites && <dl className="grid h-fit grid-cols-[1fr_auto] gap-x-4 gap-y-1">
            {[['Tiempo máximo', `${sb.limites.tiempo_pared_s} s`], ['CPU', `${sb.limites.cpu_s} s`], ...(sb.limites.por_prueba_s ? [['Por cada prueba', `${sb.limites.por_prueba_s} s`]] : []), ['Memoria', `${sb.limites.memoria_mb} MB`], ['Acceso a red', sb.limites.red]].map(([k, val]) => <div key={k} className="contents"><dt className="text-grafito">{k}</dt><dd className="num text-right">{val}</dd></div>)}</dl>}
        </div>
      </Seccion>
    </div>
  )
}

function Trazabilidad({ ev, esDocente }) {
  const t = ev.trazabilidad
  const { datos: auditoria } = useDatos(() => (esDocente ? api.get(`/evaluaciones/${ev.id}/auditoria`) : Promise.resolve([])), [ev.id, ev.estado, ev.nota])
  const fila = (k, v) => <div className="contents" key={k}><dt className="text-grafito">{k}</dt><dd className="break-all">{v}</dd></div>
  return (
    <div className="space-y-5">
      <Seccion titulo="Con qué se generó esta evaluación">
        <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-[14rem_1fr]">
          {fila('Modelo', `${t.proveedor} · ${t.modelo}${t.parametros?.version_modelo_informada && t.parametros.version_modelo_informada !== t.modelo ? ` (el servicio informó ${t.parametros.version_modelo_informada})` : ''}`)}
          {fila('Temperatura', t.parametros?.temperatura ?? 'la predeterminada del proveedor')}
          {fila('Salida estructurada', t.parametros?.salida_estructurada)}
          {fila('Pasadas de consistencia', t.parametros?.pasadas_consistencia)}
          {t.parametros?.reutilizada_de_evaluacion && fila('Resultado reutilizado', `de la evaluación n.º ${t.parametros.reutilizada_de_evaluacion} (misma evidencia, rúbrica y modelo)`)}
          {fila('Versión del prompt', t.prompt_version)}
          {fila('Rúbrica', <Link className="text-petroleo underline" to={`/app/rubricas/${ev.rubrica.id}`}>versión {t.rubrica_version}</Link>)}
          {fila('Huella de la rúbrica', <span className="num text-sm">{t.rubrica_hash}</span>)}
          {fila('Huella de las evidencias', <span className="num text-sm">{t.hash_evidencias}</span>)}
          {fila('Tokens usados', t.uso?.tokens_total ?? '—')}
          {fila('Duración', `${fmtNum(t.duracion_s)} s`)}
          {t.aprobado_en && fila('Aprobada', fmtFechaHora(t.aprobado_en))}
          {t.publicado_en && fila('Publicada', fmtFechaHora(t.publicado_en))}
        </dl>
        <p className="mt-4 text-sm text-grafito">{ev.calculo.formula}</p>
      </Seccion>
      <Seccion titulo="Evidencias analizadas">
        {(t.evidencias.advertencias || []).map((a, i) => <div key={i} className="mb-3"><Aviso tono="aviso">{a}</Aviso></div>)}
        <div className="overflow-x-auto"><table className="tabla w-full text-[0.95rem]"><thead><tr><th>Fuente</th><th>Tipo</th><th className="text-right">Caracteres</th><th>Huella</th></tr></thead><tbody>
          {t.evidencias.fuentes.map((f) => <tr key={f.id}><td>{f.titulo}</td><td className="text-grafito">{f.tipo}</td><td className="num text-right">{f.caracteres.toLocaleString('es-CO')}</td><td className="num text-sm text-grafito">{f.sha256}</td></tr>)}
        </tbody></table></div>
        {t.evidencias.imagenes?.length > 0 && <p className="mt-3 text-grafito">Imágenes enviadas al modelo: {t.evidencias.imagenes.join(', ')}</p>}
        <div className="mt-4"><Evidencias e={ev.entrega} /></div>
      </Seccion>
      {esDocente && auditoria && (
        <Seccion titulo="Registro de auditoría">
          <ol className="space-y-3">
            {auditoria.map((a) => (
              <li key={a.id} className="border-l-2 border-linea pl-3.5">
                <p><span className="font-medium">{fmtAccion(a.accion)}</span> <span className="text-grafito">· {a.usuario} · {fmtFechaHora(a.creado_en)}</span></p>
                {a.detalle?.criterio && <p className="text-[0.95rem]">{a.detalle.criterio}: nota {fmtNota(a.detalle.nota_antes)} → {fmtNota(a.detalle.nota_despues)}. {a.detalle.comentario}</p>}
                {a.detalle?.nota_preliminar != null && <p className="text-[0.95rem] text-grafito">Nota preliminar {fmtNota(a.detalle.nota_preliminar)} · {a.detalle.modelo}</p>}
              </li>))}
          </ol>
        </Seccion>)}
    </div>
  )
}

export default function Evaluacion() {
  const { id } = useParams()
  const { esDocente } = useAuth()
  const { datos: ev, error, cargando, recargar, fijar } = useDatos(() => api.get(`/evaluaciones/${id}`), [id])
  const [pestana, setPestana] = useState('valoracion')
  const [ajuste, setAjuste] = useState(null)
  const [fuente, setFuente] = useState(null)
  const [ocupado, setOcupado] = useState('')
  const [errorAccion, setErrorAccion] = useState('')
  const [obs, setObs] = useState(null)

  const enCurso = ev && ['en_cola', 'procesando'].includes(ev.estado)
  useEffect(() => {
    if (!enCurso) return
    const t = setInterval(() => recargar(true), 2500)
    return () => clearInterval(t)
  }, [enCurso, recargar])
  useEffect(() => { if (ev) setObs(ev.observacion_docente || '') }, [ev?.id, ev?.observacion_docente]) // eslint-disable-line react-hooks/exhaustive-deps

  if (cargando) return <Pagina titulo="Evaluación"><Cargando /></Pagina>
  if (error) return <Pagina titulo="Evaluación"><Aviso tono="grave">{error}</Aviso></Pagina>
  const migas = <Link to={`/app/laboratorios/${ev.laboratorio.id}`} className="underline">{ev.laboratorio.titulo}</Link>
  const titulo = esDocente ? ev.estudiante.nombre : 'Tu evaluación'
  if (enCurso) return <Pagina titulo={titulo} migas={migas}><Aviso tono="info" titulo="Evaluación en curso">{ev.progreso || 'En cola'}…</Aviso></Pagina>
  if (ev.estado === 'error') return <Pagina titulo={titulo} migas={migas}><Aviso tono="grave" titulo="La evaluación no pudo completarse">{ev.error}<br />Vuelve al laboratorio y solicítala de nuevo.</Aviso></Pagina>
  if (!ev.visible) return <Pagina titulo={titulo} migas={migas}><Aviso tono="info" titulo="Tu docente está revisando esta evaluación">La IA ya generó una valoración preliminar. La verás aquí cuando tu docente la revise y la publique.</Aviso></Pagina>

  const accion = async (nombre) => {
    setOcupado(nombre); setErrorAccion('')
    try { fijar(await api.post(`/evaluaciones/${id}/${nombre}`)) } catch (e) { setErrorAccion(e.message) } finally { setOcupado('') }
  }
  const guardarObs = async () => {
    setOcupado('obs')
    try { fijar(await api.patch(`/evaluaciones/${id}`, { observacion_docente: obs })) } catch (e) { setErrorAccion(e.message) } finally { setOcupado('') }
  }
  const r = ev.resultado, rub = ev.rubrica.contenido
  const editable = esDocente && ['preliminar', 'aprobada'].includes(ev.estado)
  const simulado = ev.trazabilidad.proveedor === 'simulado'
  const alertasCrit = r.criterios.reduce((a, c) => a + c.alertas.length, 0)
  const criterios = r.criterios.map((c) => ({ ...c, descriptores_nivel: rub.criterios.find((x) => x.id === c.criterio_id)?.descriptores[c.nivel_id] }))

  return (
    <Pagina titulo={titulo} migas={migas}
      bajada={<span className="flex flex-wrap items-center gap-2">{ev.laboratorio.cohorte} · entrega {ev.entrega.numero} <Estado valor={ev.estado} /></span>}
      acciones={esDocente && <>
        {ev.estado === 'preliminar' && <Boton variante="secundario" icono={BadgeCheck} ocupado={ocupado === 'aprobar'} onClick={() => accion('aprobar')}>Aprobar</Boton>}
        {['preliminar', 'aprobada'].includes(ev.estado) && <Boton icono={Send} ocupado={ocupado === 'publicar'} onClick={() => accion('publicar')}>{ev.estado === 'preliminar' ? 'Aprobar y publicar' : 'Publicar al estudiante'}</Boton>}
        {['aprobada', 'publicada'].includes(ev.estado) && <Boton variante="secundario" icono={RotateCcw} ocupado={ocupado === 'reabrir'} onClick={() => accion('reabrir')}>Reabrir para ajustar</Boton>}
      </>}>
      <div className="space-y-4">
        {errorAccion && <Aviso tono="grave">{errorAccion}</Aviso>}
        {ev.es_preliminar && <Aviso tono="aviso" titulo={esDocente ? 'Valoración preliminar generada con asistencia de IA' : 'Valoración preliminar, aún sin validar por tu docente'}>
          {esDocente ? 'El estudiante todavía no la ve. Revisa cada criterio, ajusta lo que no compartas y publícala.' : 'Puede cambiar cuando tu docente la revise.'}</Aviso>}
        {simulado && <Aviso tono="aviso" titulo="Generada en modo simulado">No intervino un modelo de IA: los niveles salen de una heurística de coincidencia de términos. Sirve para probar el flujo, no como valoración pedagógica.</Aviso>}
        {esDocente && r.alertas.map((a, i) => <Aviso key={i} tono="grave">{a}</Aviso>)}
      </div>

      <section className="mt-5 grid gap-6 rounded-xl border border-linea bg-white p-5 lg:grid-cols-[minmax(0,22rem)_1fr]">
        <div>
          <p className="text-sm text-grafito">{ev.estado === 'publicada' ? 'Nota del laboratorio' : ev.estado === 'aprobada' ? 'Nota aprobada, sin publicar' : 'Nota preliminar'}</p>
          <Regla nota={ev.nota} grande etiqueta="Nota" />
          <p className="mt-3 text-sm text-grafito">Calculada por el servidor a partir de los niveles y las ponderaciones de la rúbrica v{ev.rubrica.version}.</p>
        </div>
        <div className="min-w-0">
          <p className="max-w-[75ch] text-[1.03rem]">{r.resumen}</p>
          {esDocente && <p className="mt-3 text-sm text-grafito">{r.citas.verificadas} de {r.citas.total} citas verificadas contra la entrega{r.citas.no_verificadas > 0 && <span className="font-medium text-grave"> · {r.citas.no_verificadas} no encontradas</span>}{alertasCrit > 0 && <span className="text-aviso"> · {alertasCrit} alertas en criterios</span>}</p>}
        </div>
      </section>

      <div className="mt-6">
        <Pestanas opciones={[['valoracion', 'Valoración'], ['verificacion', 'Verificación técnica'], ['trazabilidad', 'Trazabilidad']]} valor={pestana} onCambio={setPestana} />
      </div>

      {pestana === 'valoracion' && (
        <div className="space-y-5">
          <div className="grid gap-5 lg:grid-cols-3">
            <Seccion titulo="Qué aprendiste"><Lista items={r.que_aprendio} /></Seccion>
            <Seccion titulo="Cómo lo aplicaste"><Lista items={r.como_lo_aplico} /></Seccion>
            <Seccion titulo="Qué fortalecer"><Lista items={r.que_fortalecer} /></Seccion>
          </div>
          <Seccion titulo="Cómo se calculó la nota">
            <div className="overflow-x-auto">
              <table className="tabla w-full">
                <thead><tr><th>Criterio</th><th>Nivel</th><th className="text-right">Puntaje</th><th className="text-right">Peso</th><th className="text-right">Aporte</th></tr></thead>
                <tbody>
                  {ev.calculo.desglose.map((d) => <tr key={d.criterio_id}><td>{d.criterio}</td><td>{d.nivel || <span className="text-grave">Sin valorar</span>}{d.origen_puntaje === 'ajuste docente' && <span className="text-sm text-grafito"> · puntaje del docente</span>}</td><td className="num text-right">{fmtNota(d.puntaje)}</td><td className="num text-right">{d.ponderacion} %</td><td className="num text-right">{d.aporte.toFixed(3).replace('.', ',')}</td></tr>)}
                  <tr><td colSpan={4} className="text-right font-medium">Suma ponderada → nota redondeada a un decimal</td><td className="num text-right font-bold">{ev.calculo.suma_exacta.toFixed(3).replace('.', ',')} → {fmtNota(ev.calculo.nota)}</td></tr>
                </tbody>
              </table>
            </div>
          </Seccion>
          <h2 className="pt-2 text-xl font-bold">Valoración por criterio</h2>
          {criterios.map((c) => <Criterio key={c.criterio_id} c={c} rubrica={rub} editable={editable} onAjustar={setAjuste} onVer={setFuente} />)}
          <div className="grid gap-5 lg:grid-cols-2">
            <Seccion titulo="Recomendaciones para ti"><Lista items={r.recomendaciones} /></Seccion>
            <Seccion titulo="Temas de IA que trabajaste">
              {r.temas.length === 0 ? <p className="text-grafito">No se identificaron temas.</p> : (
                <ul className="space-y-3">{r.temas.map((t) => <li key={t.tema_id + t.nombre}><p className="flex flex-wrap items-center gap-2 font-medium">{t.nombre}<Dominio puntaje={t.dominio} /></p><p className="text-[0.95rem] text-grafito">{t.aprendizaje_evidenciado}</p></li>)}</ul>)}
            </Seccion>
          </div>
          {(esDocente || ev.observacion_docente) && (
            <Seccion titulo="Observación del docente">
              {editable ? <>
                <textarea className="campo" value={obs ?? ''} onChange={(e) => setObs(e.target.value)} placeholder="Mensaje para el estudiante (opcional)" aria-label="Observación del docente" />
                <div className="mt-2 flex justify-end"><Boton variante="secundario" ocupado={ocupado === 'obs'} disabled={obs === (ev.observacion_docente || '')} onClick={guardarObs}>Guardar observación</Boton></div>
              </> : <p className="whitespace-pre-line">{ev.observacion_docente || 'Sin observación.'}</p>}
            </Seccion>)}
        </div>
      )}
      {pestana === 'verificacion' && <Verificacion v={ev.verificacion} />}
      {pestana === 'trazabilidad' && <Trazabilidad ev={ev} esDocente={esDocente} />}

      {ajuste && <ModalAjuste evaluacion={ev} criterio={ajuste} rubrica={rub} onCerrar={() => setAjuste(null)} onGuardado={(d) => { fijar(d); setAjuste(null) }} />}
      {fuente && <VisorFuente evaluacionId={ev.id} cita={fuente} onCerrar={() => setFuente(null)} />}
    </Pagina>
  )
}
