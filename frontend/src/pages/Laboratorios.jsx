import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { api, fmtFecha } from '../api'
import { Aviso, Boton, Campo, Cargando, Modal, Pagina, Vacio, useDatos } from '../ui.jsx'

export function FormularioLab({ inicial, cohortes, onGuardar, onCancelar }) {
  const [f, setF] = useState(inicial)
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const cambiar = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const enviar = async (e) => {
    e.preventDefault(); setOcupado(true); setError('')
    try { await onGuardar({ ...f, cohorte_id: Number(f.cohorte_id), orden: Number(f.orden) || 1, fecha: f.fecha || null }) }
    catch (err) { setError(err.message); setOcupado(false) }
  }
  return (
    <form onSubmit={enviar} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-[1fr_7rem_10rem]">
        <Campo etiqueta="Cohorte"><select className="campo" value={f.cohorte_id} onChange={cambiar('cohorte_id')}>{cohortes.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}</select></Campo>
        <Campo etiqueta="Orden"><input className="campo" type="number" min="1" value={f.orden} onChange={cambiar('orden')} /></Campo>
        <Campo etiqueta="Fecha"><input className="campo" type="date" value={f.fecha || ''} onChange={cambiar('fecha')} /></Campo>
      </div>
      <Campo etiqueta="Título"><input className="campo" required minLength={3} value={f.titulo} onChange={cambiar('titulo')} /></Campo>
      <Campo etiqueta="Descripción" ayuda="Qué debía construir el estudiante. La IA la usa como contexto."><textarea className="campo" required value={f.descripcion} onChange={cambiar('descripcion')} /></Campo>
      <Campo etiqueta="Objetivos" ayuda="Uno por línea."><textarea className="campo" required value={f.objetivos} onChange={cambiar('objetivos')} /></Campo>
      <Campo etiqueta="Pruebas del docente (opcional)" ayuda="Código pytest que se ejecuta en el sandbox contra cada entrega. Importa los módulos tal como deben llamarse en la solución.">
        <textarea className="campo font-mono text-sm" spellCheck={false} value={f.pruebas_docente || ''} onChange={cambiar('pruebas_docente')} placeholder={'from busqueda import bfs\n\ndef test_ruta():\n    assert bfs(...)'} />
      </Campo>
      {error && <Aviso tono="grave">{error}</Aviso>}
      <div className="flex justify-end gap-2"><Boton type="button" variante="secundario" onClick={onCancelar}>Cancelar</Boton><Boton type="submit" ocupado={ocupado}>Guardar laboratorio</Boton></div>
    </form>
  )
}

export default function Laboratorios() {
  const { datos, error, cargando } = useDatos(() => api.get('/cohortes'))
  const [nuevo, setNuevo] = useState(null)
  const navegar = useNavigate()
  if (cargando) return <Pagina titulo="Laboratorios y rúbricas"><Cargando /></Pagina>
  if (error) return <Pagina titulo="Laboratorios y rúbricas"><Aviso tono="grave">{error}</Aviso></Pagina>
  return (
    <Pagina titulo="Laboratorios y rúbricas" bajada="Cada laboratorio necesita descripción, objetivos y una rúbrica validada antes de poder evaluar entregas."
      acciones={<Boton icono={Plus} onClick={() => setNuevo({ cohorte_id: datos[0]?.id, orden: 1, titulo: '', descripcion: '', objetivos: '', fecha: '', pruebas_docente: '' })}>Crear laboratorio</Boton>}>
      <div className="space-y-8">
        {datos.map((c) => (
          <section key={c.id}>
            <h2 className="text-xl font-bold">{c.nombre}{c.periodo && <span className="ml-2 text-base font-normal text-grafito">{c.periodo}</span>}</h2>
            {c.laboratorios.length === 0
              ? <div className="mt-3"><Vacio titulo="Sin laboratorios en esta cohorte" accion={<Boton icono={Plus} variante="secundario" onClick={() => setNuevo({ cohorte_id: c.id, orden: 1, titulo: '', descripcion: '', objetivos: '', fecha: '', pruebas_docente: '' })}>Crear el primero</Boton>}>Crea el laboratorio y luego carga su rúbrica.</Vacio></div>
              : (
                <div className="mt-3 overflow-x-auto rounded-xl border border-linea bg-white">
                  <table className="tabla w-full">
                    <thead><tr><th className="w-10">N.º</th><th>Laboratorio</th><th>Rúbrica</th><th className="text-right">Entregas</th><th className="text-right">Por revisar</th></tr></thead>
                    <tbody>
                      {c.laboratorios.map((l) => (
                        <tr key={l.id}>
                          <td className="num text-grafito">{l.orden}</td>
                          <td><Link to={`/app/laboratorios/${l.id}`} className="font-medium hover:underline">{l.titulo}</Link>{l.fecha && <span className="block text-sm text-grafito">{fmtFecha(l.fecha)}</span>}
                            {!l.tiene_descripcion && <span className="block text-sm text-aviso">Falta descripción u objetivos</span>}</td>
                          <td>{l.rubrica ? <span>Validada · v{l.rubrica.version}</span> : <span className="font-medium text-aviso">Sin validar</span>}
                            {l.rubrica_borradores > 0 && <span className="block text-sm text-grafito">{l.rubrica_borradores} borrador{l.rubrica_borradores > 1 && 'es'}</span>}</td>
                          <td className="num text-right">{l.entregas}</td>
                          <td className="num text-right">{l.por_revisar || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
          </section>
        ))}
      </div>
      {nuevo && (
        <Modal titulo="Crear laboratorio" onCerrar={() => setNuevo(null)}>
          <FormularioLab inicial={nuevo} cohortes={datos} onCancelar={() => setNuevo(null)}
            onGuardar={async (f) => { const r = await api.post('/laboratorios', f); navegar(`/app/laboratorios/${r.id}`) }} />
        </Modal>
      )}
    </Pagina>
  )
}
