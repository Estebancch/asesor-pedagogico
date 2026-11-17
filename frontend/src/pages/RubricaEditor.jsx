import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, Plus, Save, Scale, Trash2 } from 'lucide-react'
import { api, fmtFecha } from '../api'
import { Aviso, Boton, Campo, Cargando, Pagina, Seccion, useDatos } from '../ui.jsx'
import { TablaRubrica } from './Laboratorio.jsx'

const nuevoId = (p) => `${p}_${Math.random().toString(36).slice(2, 8)}`
const VERIFICACIONES = [['', 'Sin regla objetiva'], ['sintaxis', 'Validación de sintaxis'], ['analisis_estatico', 'Análisis estático'], ['pruebas', 'Pruebas unitarias']]

function Inconsistencias({ lista, suma, notas, onNormalizar, ocupado }) {
  const errores = lista.filter((i) => i.severidad === 'error')
  const avisos = lista.filter((i) => i.severidad === 'advertencia')
  const ok = Math.abs(suma - 100) < 0.01
  return (
    <aside className="space-y-4 lg:sticky lg:top-4" aria-live="polite">
      <div className="rounded-xl border border-linea bg-white p-4">
        <p className="text-sm text-grafito">Suma de ponderaciones</p>
        <p className={`num titulo text-3xl font-bold ${ok ? 'text-petroleo-oscuro' : 'text-grave'}`}>{String(suma).replace('.', ',')} %</p>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-dom-0"><div className={`h-full ${ok ? 'bg-petroleo' : 'bg-grave'}`} style={{ width: `${Math.min(suma, 100)}%` }} /></div>
        {!ok && <Boton variante="secundario" icono={Scale} className="mt-3 w-full" ocupado={ocupado} onClick={onNormalizar}>Normalizar a 100 %</Boton>}
        {!ok && <p className="mt-2 text-sm text-grafito">Reparte los pesos en la misma proporción. Guarda antes los cambios que quieras conservar.</p>}
      </div>
      <div className="rounded-xl border border-linea bg-white p-4">
        <h2 className="text-lg font-bold">{errores.length ? `${errores.length} ${errores.length === 1 ? 'inconsistencia impide' : 'inconsistencias impiden'} evaluar` : 'Sin inconsistencias que impidan evaluar'}</h2>
        <ul className="mt-3 space-y-3">
          {errores.map((i, k) => <li key={k} className="border-l-2 border-grave pl-3"><p>{i.mensaje}</p>{i.sugerencia && <p className="text-sm text-grafito">{i.sugerencia}</p>}</li>)}
          {avisos.map((i, k) => <li key={`a${k}`} className="border-l-2 border-aviso pl-3"><p>{i.mensaje}</p>{i.sugerencia && <p className="text-sm text-grafito">{i.sugerencia}</p>}</li>)}
        </ul>
        {avisos.length > 0 && <p className="mt-3 text-sm text-grafito">Las marcadas en ámbar son advertencias: conviene revisarlas, pero no bloquean.</p>}
      </div>
      {notas?.length > 0 && (
        <div className="rounded-xl border border-linea bg-white p-4">
          <h2 className="font-bold">Notas de la interpretación del archivo</h2>
          <ul className="mt-2 list-disc space-y-1.5 pl-5 text-[0.95rem]">{notas.map((n, i) => <li key={i}>{n}</li>)}</ul>
        </div>)}
    </aside>
  )
}

export default function RubricaEditor() {
  const { id } = useParams()
  const navegar = useNavigate()
  const { datos, error, cargando, fijar } = useDatos(() => api.get(`/rubricas/${id}`), [id])
  const [r, setR] = useState(null)
  const [revision, setRevision] = useState({ inconsistencias: [], suma: 0 })
  const [sucio, setSucio] = useState(false)
  const [ocupado, setOcupado] = useState('')
  const [mensaje, setMensaje] = useState(null)
  const temporizador = useRef(null)

  useEffect(() => {
    if (!datos) return
    setR(datos.contenido); setSucio(false)
    setRevision({ inconsistencias: datos.inconsistencias, suma: Math.round(datos.contenido.criterios.reduce((a, c) => a + Number(c.ponderacion || 0), 0) * 100) / 100 })
  }, [datos])

  const cambiar = (nueva) => {
    setR(nueva); setSucio(true); setMensaje(null)
    clearTimeout(temporizador.current)
    temporizador.current = setTimeout(async () => {
      try { const v = await api.post('/rubricas/comprobar', nueva); setRevision({ inconsistencias: v.inconsistencias, suma: v.suma_ponderaciones }) } catch { /* se valida al guardar */ }
    }, 450)
  }
  useEffect(() => () => clearTimeout(temporizador.current), [])

  if (cargando || (datos && !r)) return <Pagina titulo="Rúbrica"><Cargando /></Pagina>
  if (error) return <Pagina titulo="Rúbrica"><Aviso tono="grave">{error}</Aviso></Pagina>
  const migas = <Link to={`/app/laboratorios/${datos.laboratorio_id}`} className="underline">Volver al laboratorio</Link>

  if (datos.estado === 'validada') {
    return (
      <Pagina titulo={datos.contenido.titulo || 'Rúbrica'} migas={migas} bajada={`Versión ${datos.version} · validada el ${fmtFecha(datos.validada_en)} · origen: ${datos.origen}`}
        acciones={<Boton icono={Plus} ocupado={ocupado === 'copia'} onClick={async () => { setOcupado('copia'); const rv = await api.post(`/laboratorios/${datos.laboratorio_id}/rubricas`, { desde_version: datos.id }); navegar(`/app/rubricas/${rv.id}`); setOcupado('') }}>Crear nueva versión</Boton>}>
        <Aviso tono="info">Esta versión está fijada y no se puede modificar: las evaluaciones que la usaron dependen de ella. Para cambiarla, crea una nueva versión.</Aviso>
        <div className="mt-5 rounded-xl border border-linea bg-white p-5"><TablaRubrica rubrica={datos.contenido} /></div>
        <p className="num mt-3 break-all text-sm text-grafito">Huella SHA-256: {datos.hash}</p>
      </Pagina>
    )
  }

  const errores = revision.inconsistencias.filter((i) => i.severidad === 'error').length
  const guardar = async () => {
    setOcupado('guardar')
    try { const rv = await api.put(`/rubricas/${id}`, r); fijar(rv); setMensaje({ tono: 'ok', texto: 'Borrador guardado.' }); return rv }
    catch (e) { setMensaje({ tono: 'grave', texto: e.message }) } finally { setOcupado('') }
  }
  const validar = async () => {
    const rv = sucio ? await guardar() : datos
    if (!rv) return
    setOcupado('validar')
    try { fijar(await api.post(`/rubricas/${id}/validar`)) } catch (e) { setMensaje({ tono: 'grave', texto: e.message }) } finally { setOcupado('') }
  }
  const normalizar = async () => {
    if (sucio && !(await guardar())) return
    setOcupado('normalizar')
    try { fijar(await api.post(`/rubricas/${id}/normalizar`)) } catch (e) { setMensaje({ tono: 'grave', texto: e.message }) } finally { setOcupado('') }
  }
  const eliminar = async () => {
    if (!window.confirm('¿Eliminar este borrador?')) return
    await api.del(`/rubricas/${id}`); navegar(`/app/laboratorios/${datos.laboratorio_id}`)
  }
  const edNivel = (i, k, v) => cambiar({ ...r, niveles: r.niveles.map((n, j) => (j === i ? { ...n, [k]: v } : n)) })
  const edComp = (i, k, v) => cambiar({ ...r, competencias: r.competencias.map((c, j) => (j === i ? { ...c, [k]: v } : c)) })
  const edCrit = (i, cambios) => cambiar({ ...r, criterios: r.criterios.map((c, j) => (j === i ? { ...c, ...cambios } : c)) })
  const num = (v) => (v === '' ? 0 : Number(v))

  return (
    <Pagina titulo="Corregir y validar la rúbrica" migas={migas} bajada={`Borrador · versión ${datos.version} · origen: ${datos.origen}${datos.interpretada_por ? ` (${datos.interpretada_por})` : ''}`}
      acciones={<>
        <Boton variante="fantasma" icono={Trash2} onClick={eliminar}>Eliminar borrador</Boton>
        <Boton variante="secundario" icono={Save} ocupado={ocupado === 'guardar'} disabled={!sucio} onClick={guardar}>Guardar borrador</Boton>
        <Boton icono={CheckCircle2} ocupado={ocupado === 'validar'} disabled={errores > 0} onClick={validar} title={errores ? 'Corrige las inconsistencias para poder validar' : ''}>Validar y fijar versión</Boton>
      </>}>
      {mensaje && <div className="mb-4"><Aviso tono={mensaje.tono}>{mensaje.texto}</Aviso></div>}
      <div className="grid items-start gap-6 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-5">
          <Seccion titulo="Datos generales">
            <Campo etiqueta="Título de la rúbrica"><input className="campo" value={r.titulo} onChange={(e) => cambiar({ ...r, titulo: e.target.value })} /></Campo>
          </Seccion>

          <Seccion titulo="Niveles de valoración" extra={<Boton variante="fantasma" icono={Plus} onClick={() => cambiar({ ...r, niveles: [...r.niveles, { id: nuevoId('nivel'), nombre: '', puntaje: 0, descripcion: '' }] })}>Agregar nivel</Boton>}>
            <p className="mb-3 text-grafito">Cada nivel vale un puntaje entre 0,0 y 5,0. La nota se calcula con estos puntajes y las ponderaciones.</p>
            <ul className="space-y-2">
              {r.niveles.map((n, i) => (
                <li key={n.id} className="flex items-center gap-2">
                  <input className="campo flex-1" aria-label={`Nombre del nivel ${i + 1}`} placeholder="Nombre del nivel" value={n.nombre} onChange={(e) => edNivel(i, 'nombre', e.target.value)} />
                  <input className="campo num w-24" type="number" step="0.1" min="0" max="5" aria-label={`Puntaje de ${n.nombre || 'nivel'}`} value={n.puntaje} onChange={(e) => edNivel(i, 'puntaje', num(e.target.value))} />
                  <Boton variante="fantasma" icono={Trash2} aria-label={`Quitar nivel ${n.nombre}`} onClick={() => cambiar({ ...r, niveles: r.niveles.filter((_, j) => j !== i) })} />
                </li>))}
            </ul>
          </Seccion>

          <Seccion titulo="Competencias" extra={<Boton variante="fantasma" icono={Plus} onClick={() => cambiar({ ...r, competencias: [...r.competencias, { id: nuevoId('comp'), nombre: '', descripcion: '' }] })}>Agregar competencia</Boton>}>
            <ul className="space-y-2">
              {r.competencias.map((c, i) => (
                <li key={c.id} className="flex items-center gap-2">
                  <input className="campo flex-1" aria-label={`Competencia ${i + 1}`} placeholder="Nombre de la competencia" value={c.nombre} onChange={(e) => edComp(i, 'nombre', e.target.value)} />
                  <Boton variante="fantasma" icono={Trash2} aria-label={`Quitar competencia ${c.nombre}`} onClick={() => cambiar({ ...r, competencias: r.competencias.filter((_, j) => j !== i) })} />
                </li>))}
            </ul>
          </Seccion>

          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Criterios</h2>
            <Boton variante="secundario" icono={Plus} onClick={() => cambiar({ ...r, criterios: [...r.criterios, { id: nuevoId('crit'), nombre: '', descripcion: '', competencia_id: r.competencias[0]?.id || '', ponderacion: 0, descriptores: {}, regla: null }] })}>Agregar criterio</Boton>
          </div>
          {r.criterios.map((c, i) => (
            <section key={c.id} className="rounded-xl border border-linea bg-white p-5">
              <div className="grid gap-3 sm:grid-cols-[1fr_7rem_auto]">
                <Campo etiqueta={`Criterio ${i + 1}`}><input className="campo" value={c.nombre} onChange={(e) => edCrit(i, { nombre: e.target.value })} /></Campo>
                <Campo etiqueta="Peso (%)"><input className="campo num" type="number" step="0.5" min="0" max="100" value={c.ponderacion} onChange={(e) => edCrit(i, { ponderacion: num(e.target.value) })} /></Campo>
                <div className="flex items-end"><Boton variante="fantasma" icono={Trash2} aria-label={`Quitar criterio ${c.nombre}`} onClick={() => cambiar({ ...r, criterios: r.criterios.filter((_, j) => j !== i) })} /></div>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <Campo etiqueta="Competencia que evalúa">
                  <select className="campo" value={c.competencia_id} onChange={(e) => edCrit(i, { competencia_id: e.target.value })}>
                    <option value="">Sin asignar</option>{r.competencias.map((k) => <option key={k.id} value={k.id}>{k.nombre || '(sin nombre)'}</option>)}
                  </select>
                </Campo>
                <Campo etiqueta="Qué se observa (opcional)"><input className="campo" value={c.descripcion} onChange={(e) => edCrit(i, { descripcion: e.target.value })} /></Campo>
              </div>
              <p className="mb-1.5 mt-4 text-sm font-medium">Descriptores de desempeño</p>
              <div className="grid gap-3 sm:grid-cols-2">
                {r.niveles.map((n) => (
                  <label key={n.id} className="block">
                    <span className="mb-1 block text-sm text-grafito">{n.nombre || '(nivel sin nombre)'} · {String(n.puntaje).replace('.', ',')}</span>
                    <textarea className="campo min-h-[4.5rem] text-[0.95rem]" value={c.descriptores[n.id] || ''} onChange={(e) => edCrit(i, { descriptores: { ...c.descriptores, [n.id]: e.target.value } })} />
                  </label>))}
              </div>
              <div className="mt-4 grid gap-3 rounded-lg bg-papel p-3 sm:grid-cols-2">
                <Campo etiqueta="Regla objetiva" ayuda="La aplica el servidor con el resultado del sandbox, no la IA.">
                  <select className="campo" value={c.regla?.verificacion || ''} onChange={(e) => edCrit(i, { regla: e.target.value ? { verificacion: e.target.value, nivel_tope: c.regla?.nivel_tope || r.niveles.at(-1)?.id || '' } : null })}>
                    {VERIFICACIONES.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
                  </select>
                </Campo>
                {c.regla && <Campo etiqueta="Si falla, el nivel máximo es">
                  <select className="campo" value={c.regla.nivel_tope} onChange={(e) => edCrit(i, { regla: { ...c.regla, nivel_tope: e.target.value } })}>
                    {r.niveles.map((n) => <option key={n.id} value={n.id}>{n.nombre}</option>)}
                  </select>
                </Campo>}
              </div>
            </section>
          ))}
        </div>
        <Inconsistencias lista={revision.inconsistencias} suma={revision.suma} notas={r.notas_interpretacion} onNormalizar={normalizar} ocupado={ocupado === 'normalizar'} />
      </div>
    </Pagina>
  )
}
