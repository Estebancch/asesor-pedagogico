import { Link } from 'react-router-dom'
import { api, estadoOculto, fmtNota } from '../api'
import { useAuth } from '../auth.jsx'
import { Aviso, Cargando, Estado, Pagina, Regla, Seccion, useDatos } from '../ui.jsx'

function PanelEstudiante() {
  const { usuario } = useAuth()
  const { datos, error, cargando } = useDatos(async () => {
    const [cohortes, informe] = await Promise.all([api.get('/cohortes'), api.get(`/informes/${usuario.id}`)])
    return { cohortes, informe: informe.datos }
  })
  if (cargando) return <Cargando />
  if (error) return <Aviso tono="grave">{error}</Aviso>
  const labs = datos.cohortes.flatMap((c) => c.laboratorios.map((l) => ({ ...l, cohorteNombre: c.nombre })))
  const pendientes = labs.filter((l) => !l.mi_entrega)
  const inf = datos.informe
  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_.9fr]">
      <Seccion titulo="Tu avance">
        {inf.evaluados ? <>
          <p className="text-grafito">Promedio de {inf.evaluados} {inf.evaluados === 1 ? 'laboratorio publicado' : 'laboratorios publicados'} · nivel {inf.nivel_global}</p>
          <Regla nota={inf.promedio} grande etiqueta="Promedio" />
          <p className="mt-4">{inf.tendencia.texto}</p>
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 font-medium text-petroleo">
            <Link className="underline" to="/app/informe">Ver informe integral</Link>
            <Link className="underline" to="/app/mapa">Ver mapa de competencias</Link>
          </div>
        </> : <p className="text-grafito">Cuando tu docente publique la primera evaluación, aquí verás tu promedio y tu evolución entre laboratorios.</p>}
      </Seccion>
      <Seccion titulo={pendientes.length ? `Te faltan ${pendientes.length} entregas` : 'Entregas al día'}>
        {pendientes.length === 0 && <p className="text-grafito">Ya entregaste todos los laboratorios de los dos cortes.</p>}
        <ul className="divide-y divide-linea">
          {pendientes.slice(0, 6).map((l) => (
            <li key={l.id} className="flex items-center justify-between gap-3 py-2.5">
              <span><span className="text-sm text-grafito">{l.cohorteNombre} · laboratorio {l.orden}</span><br />{l.titulo}</span>
              <Link to={`/app/laboratorios/${l.id}`} className="shrink-0 font-medium text-petroleo underline">Entregar</Link>
            </li>
          ))}
        </ul>
      </Seccion>
      <Seccion titulo="Tus laboratorios" className="lg:col-span-2">
        <div className="overflow-x-auto">
          <table className="tabla w-full">
            <thead><tr><th>Corte</th><th>Laboratorio</th><th>Estado</th><th className="text-right">Nota</th></tr></thead>
            <tbody>
              {labs.map((l) => (
                <tr key={l.id}>
                  <td className="whitespace-nowrap text-grafito">{l.cohorteNombre}</td>
                  <td><Link to={`/app/laboratorios/${l.id}`} className="font-medium hover:underline">{l.titulo}</Link></td>
                  <td>{l.mi_entrega ? (l.mi_entrega.estado_evaluacion ? <Estado valor={estadoOculto(l.mi_entrega.estado_evaluacion)} /> : <Estado valor="sin_evaluar" />) : <span className="text-grafito">Sin entrega</span>}</td>
                  <td className="num text-right font-medium">{fmtNota(l.mi_entrega?.nota)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Seccion>
    </div>
  )
}

function PanelDocente() {
  const { datos, error, cargando } = useDatos(async () => {
    const [cola, cohortes, sistema] = await Promise.all([api.get('/evaluaciones?estado=preliminar,aprobada,error'), api.get('/cohortes'), api.get('/config/sistema')])
    return { cola, cohortes, sistema }
  })
  if (cargando) return <Cargando />
  if (error) return <Aviso tono="grave">{error}</Aviso>
  const labs = datos.cohortes.flatMap((c) => c.laboratorios)
  const sinRubrica = labs.filter((l) => !l.rubrica)
  const porRevisar = datos.cola.filter((e) => e.estado === 'preliminar')
  const porPublicar = datos.cola.filter((e) => e.estado === 'aprobada')
  const s = datos.sistema
  return (
    <div className="space-y-6">
      {s.ia.proveedor === 'simulado' && (
        <Aviso tono="aviso" titulo="La plataforma está en modo simulado">
          Las evaluaciones nuevas se generan con una heurística, no con un modelo de IA. Un administrador puede conectar Gemini u otro proveedor en Administración → Modelo de IA.
        </Aviso>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <Seccion titulo={`${porRevisar.length} evaluaciones esperan tu revisión`} extra={<Link to="/app/revision" className="font-medium text-petroleo underline">Abrir la cola</Link>}>
          {porRevisar.length === 0 && <p className="text-grafito">No hay evaluaciones preliminares pendientes.</p>}
          <ul className="divide-y divide-linea">
            {porRevisar.slice(0, 5).map((e) => (
              <li key={e.id} className="flex items-center justify-between gap-3 py-2.5">
                <Link to={`/app/evaluaciones/${e.id}`} className="min-w-0 hover:underline"><span className="font-medium">{e.estudiante}</span><br /><span className="text-sm text-grafito">{e.laboratorio}</span></Link>
                <span className="num shrink-0 text-right"><span className="font-medium">{fmtNota(e.nota)}</span>{e.alertas > 0 && <><br /><span className="text-sm text-aviso">{e.alertas} alertas</span></>}</span>
              </li>
            ))}
          </ul>
          {porPublicar.length > 0 && <p className="mt-3 text-grafito">{porPublicar.length} aprobadas aún sin publicar al estudiante.</p>}
        </Seccion>
        <Seccion titulo="Estado de los laboratorios" extra={<Link to="/app/laboratorios" className="font-medium text-petroleo underline">Gestionar</Link>}>
          <p>{labs.length} laboratorios en {datos.cohortes.length} cortes · {s.totales.entregas} entregas · {s.totales.evaluaciones} evaluaciones.</p>
          {sinRubrica.length > 0
            ? <div className="mt-3"><Aviso tono="aviso" titulo={`${sinRubrica.length} sin rúbrica validada`}>No se pueden evaluar hasta validar su rúbrica: {sinRubrica.map((l) => l.titulo).join('; ')}.</Aviso></div>
            : labs.length > 0 && <p className="mt-2 text-grafito">Todos tienen una rúbrica validada.</p>}
          <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-grafito">Modelo de IA</dt><dd>{s.ia.proveedor} · {s.ia.modelo}</dd>
            <dt className="text-grafito">Sandbox</dt><dd>{s.sandbox.habilitado ? `activo · red ${s.sandbox.red} · ${s.sandbox.tiempo_s} s · ${s.sandbox.memoria_mb} MB` : 'deshabilitado'}</dd>
            <dt className="text-grafito">Base de datos</dt><dd>{s.base_datos}</dd>
          </dl>
        </Seccion>
      </div>
    </div>
  )
}

export default function Panel() {
  const { usuario, esDocente } = useAuth()
  return (
    <Pagina titulo={`Hola, ${usuario.nombre.split(' ')[0]}`} bajada={esDocente ? 'Revisa lo que propuso la IA, ajusta lo necesario y publica.' : 'Entrega tus laboratorios y consulta lo que aprendiste en cada uno.'}>
      {esDocente ? <PanelDocente /> : <PanelEstudiante />}
    </Pagina>
  )
}
