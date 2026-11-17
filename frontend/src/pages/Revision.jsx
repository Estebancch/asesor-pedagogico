import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmtFechaHora, fmtNota } from '../api'
import { Aviso, Cargando, Estado, Pagina, Pestanas, Vacio, useDatos } from '../ui.jsx'

export default function Revision() {
  const { datos, error, cargando } = useDatos(() => api.get('/evaluaciones'))
  const [filtro, setFiltro] = useState('preliminar')
  if (cargando) return <Pagina titulo="Revisión de evaluaciones"><Cargando /></Pagina>
  if (error) return <Pagina titulo="Revisión de evaluaciones"><Aviso tono="grave">{error}</Aviso></Pagina>
  const cuenta = (e) => datos.filter((x) => x.estado === e).length
  const lista = datos.filter((x) => (filtro === 'todas' ? true : x.estado === filtro))
  return (
    <Pagina titulo="Revisión de evaluaciones" bajada="Ninguna valoración llega al estudiante sin que la apruebes. Empieza por las que tienen alertas: citas no verificadas, reglas no concluyentes o baja confianza.">
      <Pestanas valor={filtro} onCambio={setFiltro} opciones={[['preliminar', 'Por revisar', cuenta('preliminar')], ['aprobada', 'Aprobadas sin publicar', cuenta('aprobada')], ['publicada', 'Publicadas'], ['error', 'Con error', cuenta('error')], ['todas', 'Todas']]} />
      {lista.length === 0 ? <Vacio titulo="Nada en esta lista">Cuando un estudiante solicite una evaluación aparecerá en «Por revisar».</Vacio> : (
        <div className="overflow-x-auto rounded-xl border border-linea bg-white">
          <table className="tabla w-full">
            <thead><tr><th>Estudiante</th><th>Laboratorio</th><th>Estado</th><th className="text-right">Nota</th><th className="text-right">Alertas</th><th>Modelo</th><th>Generada</th></tr></thead>
            <tbody>
              {[...lista].sort((a, b) => (filtro === 'preliminar' ? b.alertas - a.alertas : 0)).map((e) => (
                <tr key={e.id}>
                  <td><Link to={`/app/evaluaciones/${e.id}`} className="font-medium hover:underline">{e.estudiante}</Link></td>
                  <td>{e.laboratorio}<span className="block text-sm text-grafito">Cohorte {e.cohorte}</span></td>
                  <td><Estado valor={e.estado} />{e.error && <span className="mt-1 block max-w-xs text-sm text-grave">{e.error}</span>}</td>
                  <td className="num text-right font-medium">{fmtNota(e.nota)}</td>
                  <td className={`num text-right ${e.alertas ? 'font-medium text-aviso' : 'text-grafito'}`}>{e.alertas || '—'}</td>
                  <td className="text-sm text-grafito">{e.modelo}</td>
                  <td className="whitespace-nowrap text-sm text-grafito">{fmtFechaHora(e.creado_en)}</td>
                </tr>))}
            </tbody>
          </table>
        </div>)}
    </Pagina>
  )
}
