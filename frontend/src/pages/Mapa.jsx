import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Background, Controls, Handle, MiniMap, Position, ReactFlow, ReactFlowProvider, getViewportForBounds, useReactFlow } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { toPng } from 'html-to-image'
import { Download, List, Network, Search, TriangleAlert, X } from 'lucide-react'
import { COLOR_DOMINIO, TEXTO_DOMINIO, api, fmtNota, guardarBlob, nivelDominio } from '../api'
import { useAuth } from '../auth.jsx'
import { Aviso, Boton, Cargando, Dominio, Lista, Pagina, Vacio, useDatos } from '../ui.jsx'

const CENTRO = { top: '50%', left: '50%', transform: 'translate(-50%, -50%)', opacity: 0, pointerEvents: 'none', width: 1, height: 1, minWidth: 0, minHeight: 0, border: 0 }
const Anclas = () => <><Handle type="target" position={Position.Top} style={CENTRO} isConnectable={false} /><Handle type="source" position={Position.Top} style={CENTRO} isConnectable={false} /></>

function NodoRaiz({ data }) {
  return <div className="w-60 rounded-2xl bg-tinta px-5 py-4 text-center text-white shadow-lg"><Anclas /><p className="titulo text-xl font-bold">{data.nombre}</p><p className="text-sm text-white/75">{data.subtitulo}</p></div>
}
function NodoCategoria({ data, selected }) {
  return (
    <div className={`w-52 rounded-xl border-2 bg-white px-4 py-2.5 text-center ${selected ? 'border-tinta' : 'border-petroleo'} ${data.atenuado ? 'opacity-30' : ''}`}>
      <Anclas /><p className="titulo font-bold leading-tight">{data.nombre}</p>
      <p className="mt-0.5 text-xs text-grafito">{data.temas} {data.temas === 1 ? 'tema' : 'temas'}{data.colapsado ? ' · mostrar' : ''}</p>
    </div>)
}
function NodoTema({ data, selected }) {
  const n = nivelDominio(data.dominio)
  return (
    <div className={`w-44 rounded-lg px-3 py-2 text-center ${selected ? 'ring-[3px] ring-tinta ring-offset-2' : ''} ${data.atenuado ? 'opacity-25' : ''}`}
      style={{ background: COLOR_DOMINIO[n.paso], color: TEXTO_DOMINIO[n.paso], border: n.paso < 3 ? '1px solid #7fc5bc' : '1px solid transparent' }}>
      <Anclas /><p className="font-medium leading-tight">{data.nombre}</p>
      <p className="num mt-0.5 text-xs opacity-90">{n.etiqueta}{data.dominio != null && ` · ${fmtNota(data.dominio)}`}</p>
      {data.requiere_profundizacion && <p className="mt-1 inline-flex items-center gap-1 rounded-full bg-aviso-suave px-2 py-0.5 text-xs font-medium text-aviso"><TriangleAlert size={12} aria-hidden />Profundizar</p>}
    </div>)
}
function NodoConcepto({ data }) {
  return <div className="max-w-[10rem] rounded-full border border-linea bg-white px-2.5 py-1 text-center text-xs text-grafito"><Anclas />{data.nombre}</div>
}
// En esta versión de React Flow un número de padding son píxeles; el margen se da en porcentaje.
const AJUSTE = '7%'
const ETIQUETAS = { 'controls.ariaLabel': 'Controles del mapa', 'controls.zoomIn.ariaLabel': 'Acercar', 'controls.zoomOut.ariaLabel': 'Alejar', 'controls.fitView.ariaLabel': 'Ajustar a la vista', 'minimap.ariaLabel': 'Minimapa' }
const TIPOS = { raiz: NodoRaiz, categoria: NodoCategoria, tema: NodoTema, concepto: NodoConcepto }

/* Disposición radial: categorías alrededor del centro, temas en un anillo exterior
   dentro del sector de su categoría y conceptos (al expandir) más afuera. */
function disponer(mapa, { colapsadas, expandido, busqueda }) {
  const cats = mapa.nodos.filter((n) => n.tipo === 'categoria')
  const temasDe = (c) => mapa.nodos.filter((n) => n.tipo === 'tema' && `cat:${n.categoria}` === c.id)
  const visibles = cats.map((c) => ({ c, temas: colapsadas.has(c.id) ? [] : temasDe(c) }))
  const pesos = visibles.map((v) => Math.max(v.temas.length, 1.5))
  const total = pesos.reduce((a, b) => a + b, 0) || 1
  // Radio de las categorías: el necesario para que dos vecinas (208 px de ancho) no se monten entre sí ni sobre el centro.
  const separacion = pesos.length > 1 ? Math.min(...pesos.map((p, i) => ((p + pesos[(i + 1) % pesos.length]) / 2 / total) * 2 * Math.PI)) : Math.PI
  const r1 = Math.max(265, Math.min(250 / (2 * Math.sin(Math.min(separacion, Math.PI) / 2)), 520))
  const r2 = Math.max(430, r1 + 215, (total * 215) / (2 * Math.PI))
  const q = busqueda.trim().toLowerCase()
  const coincide = (n) => !q || n.nombre.toLowerCase().includes(q) || (n.conceptos || []).some((x) => x.toLowerCase().includes(q))
  const nodos = [{ id: 'raiz', type: 'raiz', position: { x: 0, y: 0 }, data: mapa.nodos[0], selectable: false }]
  const aristas = []
  const linea = { stroke: '#9fb1b1', strokeWidth: 1.5 }
  let angulo = -Math.PI / 2
  visibles.forEach(({ c, temas }, i) => {
    const sector = (pesos[i] / total) * 2 * Math.PI
    const medio = angulo + sector / 2
    nodos.push({ id: c.id, type: 'categoria', position: { x: Math.cos(medio) * r1, y: Math.sin(medio) * r1 },
      data: { ...c, colapsado: colapsadas.has(c.id), atenuado: q && !temasDe(c).some(coincide) } })
    aristas.push({ id: `j:${c.id}`, source: 'raiz', target: c.id, type: 'straight', style: { ...linea, strokeWidth: 2 }, selectable: false })
    temas.forEach((t, j) => {
      const a = angulo + (sector * (j + 0.5)) / temas.length
      const r = r2 + (temas.length > 3 && j % 2 ? 85 : 0)
      nodos.push({ id: t.id, type: 'tema', position: { x: Math.cos(a) * r, y: Math.sin(a) * r }, data: { ...t, atenuado: !coincide(t) } })
      aristas.push({ id: `j:${t.id}`, source: c.id, target: t.id, type: 'straight', style: linea, selectable: false })
      if (expandido === t.id) {
        const cs = t.conceptos.slice(0, 8)
        cs.forEach((nombre, k) => {
          const ac = a + (k - (cs.length - 1) / 2) * 0.115
          const id = `${t.id}:c${k}`
          nodos.push({ id, type: 'concepto', position: { x: Math.cos(ac) * (r + 185 + (k % 2) * 46), y: Math.sin(ac) * (r + 185 + (k % 2) * 46) }, data: { nombre }, selectable: false })
          aristas.push({ id: `j:${id}`, source: t.id, target: id, type: 'straight', style: { stroke: '#c8d3d3', strokeWidth: 1 }, selectable: false })
        })
      }
    })
    angulo += sector
  })
  const presentes = new Set(nodos.map((n) => n.id))
  mapa.aristas.filter((a) => a.tipo === 'relacion' && presentes.has(a.origen) && presentes.has(a.destino)).forEach((a) =>
    aristas.push({ id: a.id, source: a.origen, target: a.destino, type: 'straight', style: { stroke: '#12292e', strokeWidth: 1.25, strokeDasharray: '5 5', opacity: 0.55 }, selectable: false }))
  return { nodos, aristas }
}

function Detalle({ nodo, expandido, onExpandir, onCerrar }) {
  return (
    <div className="rounded-xl border border-linea bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div><h2 className="text-xl font-bold">{nodo.nombre}</h2><p className="mt-1 flex flex-wrap items-center gap-2"><Dominio puntaje={nodo.dominio} />{nodo.dominio != null && <span className="num text-grafito">dominio {fmtNota(nodo.dominio)} de 5,0</span>}</p></div>
        <button onClick={onCerrar} aria-label="Cerrar detalle" className="rounded-md p-1.5 text-grafito hover:bg-papel"><X size={18} /></button>
      </div>
      <h3 className="mb-1.5 mt-5 font-bold">Laboratorios donde lo aplicaste</h3>
      <ul className="divide-y divide-linea">
        {nodo.laboratorios.map((l) => (
          <li key={l.evaluacion_id} className="flex items-center justify-between gap-3 py-2">
            <Link to={`/app/evaluaciones/${l.evaluacion_id}`} className="min-w-0 hover:underline"><span className="block truncate font-medium">{l.titulo}</span><span className="text-sm text-grafito">{l.cohorte_nombre}{l.estado !== 'publicada' && ' · sin publicar'}</span></Link>
            <span className="num shrink-0 text-right text-sm"><span className="text-grafito">dominio</span> <span className="text-base font-bold">{fmtNota(l.dominio)}</span></span>
          </li>))}
      </ul>
      <h3 className="mb-1.5 mt-5 font-bold">Evidencias de aprendizaje</h3>
      <ul className="space-y-3">
        {nodo.evidencias.map((e, i) => (
          <li key={i}><p>{e.texto}</p>
            {e.citas.map((c, k) => <p key={k} className="mt-1 border-l-2 border-tinta/20 pl-3 text-[0.95rem]">«<span className="cita">{c.cita}</span>» <span className="text-sm text-grafito">({c.fuente.replace(/^codigo:/, '').replace(/^informe:p/, 'informe, pág. ')})</span></p>)}
            <p className="mt-0.5 text-sm text-grafito">{e.laboratorio}</p></li>))}
      </ul>
      {nodo.conceptos.length > 0 && <>
        <h3 className="mb-1.5 mt-5 font-bold">Conceptos trabajados</h3>
        <ul className="flex flex-wrap gap-1.5">{nodo.conceptos.map((c) => <li key={c} className="rounded-full border border-linea px-2.5 py-0.5 text-sm">{c}</li>)}</ul>
        <button className="mt-2 font-medium text-petroleo underline" onClick={onExpandir}>{expandido ? 'Ocultar conceptos en el mapa' : 'Mostrar conceptos en el mapa'}</button>
      </>}
      <h3 className="mb-1.5 mt-5 font-bold">Aspectos por profundizar</h3>
      <Lista items={nodo.aspectos} vacio="Sin aspectos pendientes registrados." />
    </div>)
}

function Lienzo({ mapa, seleccion, setSeleccion }) {
  const [colapsadas, setColapsadas] = useState(new Set())
  const [expandido, setExpandido] = useState(null)
  const [busqueda, setBusqueda] = useState('')
  const [exportando, setExportando] = useState(false)
  const flujo = useReactFlow()
  const { nodos, aristas } = useMemo(() => disponer(mapa, { colapsadas, expandido, busqueda }), [mapa, colapsadas, expandido, busqueda])
  const marcados = useMemo(() => nodos.map((n) => ({ ...n, selected: n.id === seleccion?.id })), [nodos, seleccion])
  // Con el panel de detalle abierto (pantallas anchas) el mapa se encuadra en el espacio que queda a su izquierda.
  const conPanel = Boolean(seleccion)
  useEffect(() => {
    const ancho = conPanel && window.matchMedia('(min-width: 1280px)').matches
    const padding = ancho ? { top: AJUSTE, bottom: AJUSTE, left: '4%', right: '420px' } : AJUSTE
    const t = setTimeout(() => flujo.fitView({ padding, duration: 300 }), 60)
    return () => clearTimeout(t)
  }, [mapa, colapsadas, expandido, conPanel, flujo])

  const alHacerClic = useCallback((_, nodo) => {
    if (nodo.type === 'categoria') {
      setColapsadas((prev) => { const s = new Set(prev); s.has(nodo.id) ? s.delete(nodo.id) : s.add(nodo.id); return s })
      setSeleccion(null)
    } else if (nodo.type === 'tema') setSeleccion(nodo.data)
  }, [setSeleccion])

  const descargarPng = async () => {
    setExportando(true)
    try {
      const limites = flujo.getNodesBounds(flujo.getNodes()) // la instancia tiene en cuenta que la posición es el centro del nodo
      const ancho = Math.min(Math.max(limites.width + 240, 1400), 4200), alto = Math.min(Math.max(limites.height + 240, 1000), 4200)
      const v = getViewportForBounds(limites, ancho, alto, 0.2, 2, '5%')
      const opciones = { backgroundColor: '#f4f8f7', width: ancho, height: alto, pixelRatio: 1.5,
        style: { width: `${ancho}px`, height: `${alto}px`, transform: `translate(${v.x}px, ${v.y}px) scale(${v.zoom})` } }
      const lienzo = document.querySelector('.react-flow__viewport')
      let url
      try { url = await toPng(lienzo, opciones) } catch { url = await toPng(lienzo, { ...opciones, skipFonts: true }) }
      guardarBlob(await (await fetch(url)).blob(), `mapa_competencias_${mapa.estudiante.nombre.replace(/\s+/g, '_')}.png`)
    } finally { setExportando(false) }
  }
  const descargarJson = () => guardarBlob(new Blob([JSON.stringify(mapa, null, 2)], { type: 'application/json' }), 'mapa_competencias.json')

  return (
    <div>
      <div>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <label className="relative min-w-[14rem] flex-1">
            <Search size={17} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-grafito" aria-hidden />
            <input className="campo pl-9" placeholder="Buscar un tema o concepto" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} aria-label="Buscar en el mapa" />
          </label>
          <Boton variante="secundario" icono={Download} ocupado={exportando} onClick={descargarPng}>Descargar imagen</Boton>
          <Boton variante="secundario" icono={Download} onClick={descargarJson}>Descargar datos</Boton>
        </div>
        {!seleccion && <p className="mb-3 text-grafito">Selecciona un tema para ver en qué laboratorios lo aplicaste, la evidencia de aprendizaje, tu nivel de dominio y qué profundizar. Selecciona una categoría para plegarla; arrastra y usa la rueda para moverte y acercar.</p>}
        <div className="relative">
        <div className="h-[72vh] min-h-[520px] overflow-hidden rounded-xl border border-linea bg-papel">
          <ReactFlow nodes={marcados} edges={aristas} nodeTypes={TIPOS} nodeOrigin={[0.5, 0.5]} onNodeClick={alHacerClic} onPaneClick={() => setSeleccion(null)}
            nodesDraggable nodesConnectable={false} elementsSelectable minZoom={0.15} maxZoom={2} fitView fitViewOptions={{ padding: AJUSTE }}
            zIndexMode="manual" ariaLabelConfig={ETIQUETAS} proOptions={{ hideAttribution: true }}>
            <Background color="#c9d6d5" gap={28} />
            <Controls showInteractive={false} />
            {!seleccion && <MiniMap pannable zoomable style={{ width: 150, height: 110 }} nodeColor={(n) => (n.type === 'tema' ? COLOR_DOMINIO[nivelDominio(n.data.dominio).paso] : n.type === 'raiz' ? '#12292e' : '#ffffff')} nodeStrokeColor="#55676a" maskColor="rgba(244,248,247,.7)" />}
          </ReactFlow>
        </div>
        {/* Detalle del tema: panel lateral sobre el mapa en pantallas anchas; debajo del mapa en las angostas */}
        {seleccion && (
          <aside aria-label="Detalle del tema" className="mt-4 xl:absolute xl:bottom-3 xl:right-3 xl:top-3 xl:mt-0 xl:w-[24rem] xl:overflow-y-auto xl:rounded-xl xl:shadow-xl">
            <Detalle nodo={seleccion} expandido={expandido === seleccion.id} onCerrar={() => setSeleccion(null)}
              onExpandir={() => setExpandido(expandido === seleccion.id ? null : seleccion.id)} />
          </aside>)}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-grafito">
          <span className="flex items-center gap-1.5">Nivel de dominio:{['Sin evidencia', 'Bajo', 'Básico', 'Alto', 'Superior'].map((t, i) => <span key={t} className="rounded px-2 py-0.5" style={{ background: COLOR_DOMINIO[i], color: TEXTO_DOMINIO[i] }}>{t}</span>)}</span>
          <span className="flex items-center gap-1.5"><svg width="34" height="6" aria-hidden><line x1="0" y1="3" x2="34" y2="3" stroke="#9fb1b1" strokeWidth="2" /></svg>pertenece a</span>
          <span className="flex items-center gap-1.5"><svg width="34" height="6" aria-hidden><line x1="0" y1="3" x2="34" y2="3" stroke="#12292e" strokeWidth="1.5" strokeDasharray="5 5" /></svg>temas relacionados</span>
        </div>
      </div>
    </div>
  )
}

function Tabla({ mapa }) {
  const cats = Object.fromEntries(mapa.nodos.filter((n) => n.tipo === 'categoria').map((c) => [c.id, c.nombre]))
  const temas = mapa.nodos.filter((n) => n.tipo === 'tema').sort((a, b) => (a.dominio ?? 9) - (b.dominio ?? 9))
  return (
    <div className="overflow-x-auto rounded-xl border border-linea bg-white">
      <table className="tabla w-full">
        <thead><tr><th>Tema</th><th>Categoría</th><th>Dominio</th><th>Laboratorios</th><th>Aspectos por profundizar</th></tr></thead>
        <tbody>{temas.map((t) => (
          <tr key={t.id}><td className="font-medium">{t.nombre}</td><td className="text-grafito">{cats[`cat:${t.categoria}`]}</td>
            <td className="whitespace-nowrap"><Dominio puntaje={t.dominio} /> <span className="num">{fmtNota(t.dominio)}</span></td>
            <td>{t.laboratorios.map((l) => <Link key={l.evaluacion_id} to={`/app/evaluaciones/${l.evaluacion_id}`} className="block text-petroleo underline">{l.titulo}</Link>)}</td>
            <td><Lista items={t.aspectos} vacio="—" /></td></tr>))}</tbody>
      </table>
    </div>)
}

export default function Mapa() {
  const { estudianteId } = useParams()
  const { usuario, esDocente } = useAuth()
  const sid = esDocente ? estudianteId : usuario.id
  const [cohorte, setCohorte] = useState('')
  const [alcance, setAlcance] = useState(esDocente ? 'todas' : 'publicadas')
  const [vista, setVista] = useState('mapa')
  const [seleccion, setSeleccion] = useState(null)
  const { datos: mapa, error, cargando } = useDatos(() => api.get(`/mapa/${sid}?alcance=${alcance}${cohorte ? `&cohorte=${cohorte}` : ''}`), [sid, cohorte, alcance])
  useEffect(() => setSeleccion(null), [mapa])
  if (esDocente && !estudianteId) return <Pagina titulo="Mapa de competencias"><Vacio titulo="Elige un estudiante">Abre el mapa desde el portafolio de cada estudiante.</Vacio></Pagina>
  const r = mapa?.resumen
  return (
    <Pagina titulo="Mapa de competencias en IA"
      migas={esDocente && mapa && <Link to={`/app/portafolio/${sid}`} className="underline">{mapa.estudiante.nombre}</Link>}
      bajada="Se genera con los temas identificados en cada laboratorio evaluado. El color indica tu nivel de dominio en cada tema."
      acciones={<Boton variante="secundario" icono={vista === 'mapa' ? List : Network} onClick={() => setVista(vista === 'mapa' ? 'tabla' : 'mapa')}>{vista === 'mapa' ? 'Ver como tabla' : 'Ver como mapa'}</Boton>}>
      <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2">
        <div className="flex items-center gap-1 rounded-lg border border-linea bg-white p-1" role="group" aria-label="Corte">
          {[['', 'Ambos cortes'], ['1', 'Corte 1'], ['2', 'Corte 2']].map(([v, t]) => (
            <button key={v} onClick={() => setCohorte(v)} aria-pressed={cohorte === v} className={`rounded-md px-3 py-1.5 font-medium ${cohorte === v ? 'bg-tinta text-white' : 'text-grafito hover:text-tinta'}`}>{t}</button>))}
        </div>
        {esDocente && <label className="flex items-center gap-2"><input type="checkbox" className="accent-petroleo" checked={alcance === 'todas'} onChange={(e) => setAlcance(e.target.checked ? 'todas' : 'publicadas')} />Incluir evaluaciones sin publicar</label>}
        {r && r.temas > 0 && <p className="text-grafito">{r.temas} temas en {r.categorias} categorías · {r.laboratorios_evaluados} laboratorios · dominio promedio <span className="num font-bold text-tinta">{fmtNota(r.dominio_promedio)}</span></p>}
      </div>
      {cargando && <Cargando texto="Construyendo el mapa" />}
      {error && <Aviso tono="grave">{error}</Aviso>}
      {mapa && r.temas === 0 && <Vacio titulo="Todavía no hay temas para mostrar">El mapa se llena con cada laboratorio evaluado{alcance === 'publicadas' ? ' y publicado' : ''}{cohorte ? ` de la cohorte ${cohorte}` : ''}.</Vacio>}
      {mapa && r.temas > 0 && <>
        {r.por_profundizar.length > 0 && <div className="mb-4"><Aviso tono="aviso" titulo="Temas que requieren profundización">{r.por_profundizar.join(' · ')}</Aviso></div>}
        {vista === 'mapa' ? <ReactFlowProvider><Lienzo mapa={mapa} seleccion={seleccion} setSeleccion={setSeleccion} /></ReactFlowProvider> : <Tabla mapa={mapa} />}
      </>}
    </Pagina>
  )
}
