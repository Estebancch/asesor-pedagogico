import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Download, Printer, Sparkles } from 'lucide-react'
import { COLOR_DOMINIO, api, fmtFecha, fmtNota, nivelDominio } from '../api'
import { useAuth } from '../auth.jsx'
import { Aviso, Boton, Cargando, Dominio, Estado, Lista, Pagina, Regla, Seccion, Vacio, useDatos } from '../ui.jsx'

function Evolucion({ puntos }) {
  // Una sola serie: el título la nombra, sin leyenda. Etiquetas directas solo en extremos y en el mínimo y el máximo.
  const notas = puntos.map((p) => p.nota)
  const marcados = new Set([0, puntos.length - 1, notas.indexOf(Math.max(...notas)), notas.indexOf(Math.min(...notas))])
  const corte = puntos.findIndex((p) => p.cohorte === 2)
  const Etiqueta = ({ x, y, index, value }) => (marcados.has(index) ? <text x={x} y={y - 12} textAnchor="middle" fontSize={13} fontWeight={700} fill="#12292e">{fmtNota(value)}</text> : null)
  const Punta = ({ active, payload }) => (active && payload?.length ? (
    <div className="rounded-lg border border-linea bg-white px-3 py-2 text-sm shadow-md">
      <p className="font-medium">{payload[0].payload.titulo}</p>
      <p className="text-grafito">Corte {payload[0].payload.cohorte} · nota <span className="num font-bold text-tinta">{fmtNota(payload[0].value)}</span></p>
    </div>) : null)
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <LineChart data={puntos} margin={{ top: 26, right: 24, bottom: 4, left: -18 }}>
          <CartesianGrid stroke="#e4e9e9" vertical={false} />
          <XAxis dataKey="etiqueta" padding={{ left: 22, right: 14 }} tick={{ fontSize: 13, fill: '#55676a' }} tickLine={false} axisLine={{ stroke: '#d3dddc' }} />
          <YAxis domain={[0, 5]} ticks={[0, 1, 2, 3, 4, 5]} tick={{ fontSize: 13, fill: '#55676a' }} tickLine={false} axisLine={false} />
          <ReferenceLine y={3} stroke="#55676a" strokeDasharray="4 4" label={{ value: 'Aprobación 3,0', position: 'insideBottomRight', fontSize: 12, fill: '#55676a' }} />
          {corte > 0 && <ReferenceLine x={puntos[corte].etiqueta} stroke="#d3dddc" label={{ value: 'Inicia corte 2', position: 'insideTopLeft', fontSize: 12, fill: '#55676a' }} />}
          <Tooltip content={<Punta />} cursor={{ stroke: '#12292e', strokeWidth: 1 }} />
          <Line type="linear" dataKey="nota" stroke="#0b6e69" strokeWidth={2} dot={{ r: 4.5, fill: '#0b6e69', stroke: '#fff', strokeWidth: 2 }} activeDot={{ r: 6.5 }} label={<Etiqueta />} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function Barras({ items }) {
  return (
    <ul className="space-y-3">
      {items.map((c) => {
        const n = nivelDominio(c.puntaje)
        return (
          <li key={c.nombre} title={`${c.nombre}: ${fmtNota(c.puntaje)} (${n.etiqueta}) en ${c.laboratorios} laboratorios`}>
            <div className="flex items-baseline justify-between gap-3"><span>{c.nombre}</span><span className="num shrink-0 font-bold">{fmtNota(c.puntaje)} <span className="font-normal text-grafito">{n.etiqueta}</span></span></div>
            <div className="mt-1 h-3 rounded-r bg-dom-0"><div className="h-full rounded-r" style={{ width: `${c.puntaje * 20}%`, background: COLOR_DOMINIO[n.paso], outline: n.paso < 3 ? '1px solid #7fc5bc' : 'none' }} /></div>
          </li>)
      })}
    </ul>
  )
}

export default function Informe() {
  const { estudianteId } = useParams()
  const { usuario, esDocente } = useAuth()
  const sid = esDocente ? estudianteId : usuario.id
  const [alcance, setAlcance] = useState('publicadas')
  const [ocupado, setOcupado] = useState('')
  const [errorAccion, setErrorAccion] = useState('')
  const { datos, error, cargando, fijar } = useDatos(() => api.get(`/informes/${sid}?alcance=${alcance}`), [sid, alcance])
  if (esDocente && !estudianteId) return <Pagina titulo="Informe integral"><Vacio titulo="Elige un estudiante">Abre el informe desde el portafolio de cada estudiante.</Vacio></Pagina>
  if (cargando) return <Pagina titulo="Informe integral del aprendizaje"><Cargando /></Pagina>
  if (error) return <Pagina titulo="Informe integral del aprendizaje"><Aviso tono="grave">{error}</Aviso></Pagina>
  const d = datos.datos, n = datos.narrativa
  const generar = async () => {
    setOcupado('generar'); setErrorAccion('')
    try { fijar(await api.post(`/informes/${sid}/generar?alcance=${alcance}`)) } catch (e) { setErrorAccion(e.message) } finally { setOcupado('') }
  }
  const pdf = async () => {
    setOcupado('pdf'); setErrorAccion('')
    try { await api.descargar(`/informes/${sid}/pdf?alcance=${alcance}`, `informe_integral_${d.estudiante.nombre.replace(/\s+/g, '_')}.pdf`) } catch (e) { setErrorAccion(e.message) } finally { setOcupado('') }
  }
  return (
    <Pagina titulo="Informe integral del aprendizaje"
      migas={esDocente && <Link to={`/app/portafolio/${sid}`} className="underline">{d.estudiante.nombre}</Link>}
      bajada={`${esDocente ? d.estudiante.nombre + ' · ' : ''}Consolidado de los laboratorios de los cortes 1 y 2.`}
      acciones={<>
        <Boton variante="secundario" icono={Printer} onClick={() => window.print()}>Imprimir</Boton>
        <Boton variante="secundario" icono={Download} ocupado={ocupado === 'pdf'} disabled={!d.evaluados} onClick={pdf}>Descargar PDF</Boton>
        <Boton icono={Sparkles} ocupado={ocupado === 'generar'} disabled={!d.evaluados} onClick={generar}>{n ? 'Actualizar síntesis y plan' : 'Generar síntesis y plan'}</Boton>
      </>}>
      {esDocente && (
        <div className="no-imprimir mb-5 flex flex-wrap items-center gap-3">
          <span className="text-grafito">Incluir evaluaciones:</span>
          {[['publicadas', 'Solo publicadas (lo que ve el estudiante)'], ['todas', 'También preliminares y aprobadas']].map(([v, t]) => (
            <label key={v} className="flex items-center gap-2"><input type="radio" name="alcance" className="accent-petroleo" checked={alcance === v} onChange={() => setAlcance(v)} />{t}</label>))}
        </div>)}
      {errorAccion && <div className="mb-4"><Aviso tono="grave">{errorAccion}</Aviso></div>}
      {!d.evaluados ? <Vacio titulo="Aún no hay evaluaciones para consolidar">{esDocente ? 'Publica al menos una evaluación de este estudiante, o incluye las preliminares.' : 'Tu informe aparecerá cuando tu docente publique la primera evaluación.'}</Vacio> : (
        <div className="space-y-5">
          <section className="grid gap-6 rounded-xl border border-linea bg-white p-5 lg:grid-cols-[minmax(0,22rem)_1fr]">
            <div>
              <p className="text-sm text-grafito">Promedio general · nivel {d.nivel_global}</p>
              <Regla nota={d.promedio} grande etiqueta="Promedio general" />
            </div>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
              {[['Laboratorios evaluados', `${d.evaluados} de ${d.total_laboratorios}`], ['Entregados', d.entregados], ['Promedio corte 1', fmtNota(d.promedio_por_cohorte['1'])], ['Promedio corte 2', fmtNota(d.promedio_por_cohorte['2'])]].map(([k, v]) => (
                <div key={k}><dt className="text-sm text-grafito">{k}</dt><dd className="num titulo text-2xl font-bold">{v}</dd></div>))}
            </dl>
          </section>

          {n ? (
            <Seccion titulo="Síntesis" extra={<span className="text-sm text-grafito">Redactada con {datos.narrativa_modelo} · {fmtFecha(datos.narrativa_generada_en)}</span>}>
              {datos.narrativa_desactualizada && <div className="mb-3"><Aviso tono="aviso">Hay evaluaciones nuevas o ajustadas desde que se redactó esta síntesis. Actualízala para que coincida con los datos.</Aviso></div>}
              {n.aviso && <div className="mb-3"><Aviso tono="aviso">{n.aviso}</Aviso></div>}
              <p className="max-w-[75ch] text-[1.03rem]">{n.resumen_ejecutivo}</p>
            </Seccion>
          ) : <Aviso tono="info" titulo="Falta la síntesis y el plan de fortalecimiento">Los números de este informe ya están calculados. Usa «Generar síntesis y plan» para que la IA los redacte a partir de estos datos.</Aviso>}

          <div className="grid gap-5 lg:grid-cols-2">
            <Seccion titulo="Evolución de la nota por laboratorio">
              {d.evolucion.length >= 2 ? <Evolucion puntos={d.evolucion} /> : <p className="text-grafito">Se necesita más de un laboratorio evaluado para trazar la evolución.</p>}
              <p className="mt-2">{n?.evolucion || d.tendencia.texto}</p>
            </Seccion>
            <Seccion titulo="Competencias y nivel de dominio">
              <Barras items={d.competencias} />
              <p className="mt-4 text-sm text-grafito">Promedio ponderado de los criterios que evalúan cada competencia. Bajo: menos de 3,0 · Básico: desde 3,0 · Alto: desde 4,0 · Superior: desde 4,6.</p>
            </Seccion>
          </div>

          <Seccion titulo="Valoraciones por laboratorio">
            <div className="overflow-x-auto">
              <table className="tabla w-full">
                <thead><tr><th>Corte</th><th>Laboratorio</th><th className="text-right">Nota</th><th>Nivel</th><th>Estado</th></tr></thead>
                <tbody>
                  {d.laboratorios.map((l) => (
                    <tr key={l.laboratorio_id}>
                      <td className="whitespace-nowrap text-grafito">{l.cohorte_nombre}</td>
                      <td>{l.evaluacion_id ? <Link className="font-medium hover:underline" to={`/app/evaluaciones/${l.evaluacion_id}`}>{l.titulo}</Link> : l.titulo}{l.resumen && <span className="mt-0.5 block max-w-2xl text-sm text-grafito">{l.resumen}</span>}</td>
                      <td className="num text-right font-bold">{fmtNota(l.nota)}</td>
                      <td>{l.nota != null ? <Dominio puntaje={l.nota} /> : '—'}</td>
                      <td>{l.estado ? <Estado valor={l.estado} /> : <span className="text-grafito">{l.entregado ? 'Sin evaluación en este alcance' : 'Sin entrega'}</span>}</td>
                    </tr>))}
                </tbody>
              </table>
            </div>
          </Seccion>

          <div className="grid gap-5 lg:grid-cols-2">
            <Seccion titulo="Competencias adquiridas">
              {n ? <Lista items={n.competencias_adquiridas} vacio="Aún no hay competencias en nivel Alto o Superior." /> : <Lista items={d.competencias.filter((c) => c.puntaje >= 4).map((c) => `${c.nombre} (${c.nivel})`)} vacio="Aún no hay competencias en nivel Alto o Superior." />}
            </Seccion>
            <Seccion titulo="Conocimientos aplicados" extra={<Link to={esDocente ? `/app/mapa/${sid}` : '/app/mapa'} className="no-imprimir font-medium text-petroleo underline">Ver mapa de competencias</Link>}>
              <Lista items={d.aplicaciones.slice(0, 6).map((a) => `${a.texto} (${a.laboratorio})`)} vacio="Las evaluaciones aún no registran cómo aplicaste los conocimientos." />
              <p className="mt-4 text-sm text-grafito">Temas de IA trabajados y nivel de dominio</p>
              <ul className="mt-2 flex flex-wrap gap-2">{d.temas.map((t) => <li key={t.nombre}><Dominio puntaje={t.dominio} etiqueta={`${t.nombre} · ${t.nivel}`} /></li>)}</ul>
            </Seccion>
          </div>

          <Seccion titulo="Brechas identificadas">
            {d.brechas.length === 0 ? <p className="text-grafito">No hay criterios ni competencias por debajo de 3,5.</p> : (
              <div className="overflow-x-auto">
                <table className="tabla w-full">
                  <thead><tr><th>Aspecto</th><th className="text-right">Puntaje</th><th>Dónde</th><th>Qué mejorar</th></tr></thead>
                  <tbody>{d.brechas.map((b, i) => (
                    <tr key={i}><td className="font-medium">{b.nombre}<span className="block text-sm font-normal text-grafito">{b.tipo === 'competencia' ? 'Competencia' : b.competencia}</span></td>
                      <td className="num text-right font-bold">{fmtNota(b.puntaje)}</td><td className="text-grafito">{b.laboratorio || 'Varias entregas'}</td>
                      <td>{[...b.debilidades, ...b.recomendaciones].slice(0, 2).join(' ') || '—'}</td></tr>))}</tbody>
                </table>
              </div>)}
          </Seccion>

          {n && (
            <Seccion titulo="Plan personalizado de fortalecimiento">
              {n.plan.length === 0 && <p className="text-grafito">La síntesis no incluyó acciones. Usa «Actualizar síntesis y plan» para generarlas de nuevo.</p>}
              <ol className="space-y-5">
                {n.plan.map((a, i) => (
                  <li key={i} className="grid gap-x-4 sm:grid-cols-[2.2rem_1fr]">
                    <span className="num titulo text-2xl font-bold text-petroleo" aria-hidden>{i + 1}</span>
                    <div>
                      <p className="font-bold">{a.objetivo}</p>
                      <div className="mt-1.5"><Lista items={a.acciones} /></div>
                      <p className="mt-2 text-sm text-grafito">{[a.recursos?.length ? `Recursos: ${a.recursos.join(', ')}` : '', a.plazo ? `Plazo: ${a.plazo}` : '', a.indicador ? `Lo lograste si: ${a.indicador}` : ''].filter(Boolean).join(' · ')}</p>
                    </div>
                  </li>))}
              </ol>
            </Seccion>)}
          {n?.oportunidades?.length > 0 && <Seccion titulo="Oportunidades de fortalecimiento"><Lista items={n.oportunidades} /></Seccion>}
          <p className="text-sm text-grafito">Las notas se calculan en el servidor con las ponderaciones de cada rúbrica. Las valoraciones se generan con asistencia de IA y están sujetas a revisión y aprobación docente.</p>
        </div>
      )}
    </Pagina>
  )
}
