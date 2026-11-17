import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, CircleAlert, Info, Loader2, X } from 'lucide-react'
import { COLOR_DOMINIO, ESTADOS, TEXTO_DOMINIO, fmtNota, nivelDominio } from './api'

export function useDatos(cargar, deps = []) {
  const [estado, setEstado] = useState({ datos: null, error: null, cargando: true })
  const fn = useRef(cargar)
  fn.current = cargar
  const recargar = useCallback(async (silencioso) => {
    if (!silencioso) setEstado((e) => ({ ...e, cargando: true, error: null }))
    try {
      const datos = await fn.current()
      setEstado({ datos, error: null, cargando: false })
      return datos
    } catch (e) { setEstado((s) => ({ datos: silencioso ? s.datos : null, error: e.message, cargando: false })) }
  }, [])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { recargar() }, deps)
  return { ...estado, recargar, fijar: (datos) => setEstado({ datos, error: null, cargando: false }) }
}

const BOTON = {
  primario: 'bg-petroleo text-white hover:bg-petroleo-oscuro',
  secundario: 'bg-white text-tinta border border-linea hover:border-petroleo',
  fantasma: 'text-petroleo hover:bg-petroleo-suave',
  peligro: 'bg-white text-grave border border-grave/40 hover:bg-grave-suave',
}
export function Boton({ variante = 'primario', icono: Icono, ocupado, children, className = '', ...p }) {
  return (
    <button {...p} disabled={p.disabled || ocupado}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-[0.95rem] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${BOTON[variante]} ${className}`}>
      {ocupado ? <Loader2 size={17} className="animate-spin" aria-hidden /> : Icono ? <Icono size={17} aria-hidden /> : null}
      {children}
    </button>
  )
}

export function Campo({ etiqueta, ayuda, error, children, className = '' }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-sm font-medium">{etiqueta}</span>
      {children}
      {ayuda && !error && <span className="mt-1 block text-sm text-grafito">{ayuda}</span>}
      {error && <span className="mt-1 block text-sm text-grave">{error}</span>}
    </label>
  )
}

const TONOS = {
  info: ['bg-petroleo-suave text-tinta border-petroleo/30', Info],
  ok: ['bg-petroleo-suave text-tinta border-petroleo/30', CheckCircle2],
  aviso: ['bg-aviso-suave text-tinta border-aviso/40', AlertTriangle],
  grave: ['bg-grave-suave text-tinta border-grave/40', CircleAlert],
}
export function Aviso({ tono = 'info', titulo, children, accion }) {
  const [clase, Icono] = TONOS[tono]
  return (
    <div role={tono === 'grave' ? 'alert' : 'status'} className={`flex gap-3 rounded-lg border px-3.5 py-3 ${clase}`}>
      <Icono size={19} className={`mt-0.5 shrink-0 ${tono === 'grave' ? 'text-grave' : tono === 'aviso' ? 'text-aviso' : 'text-petroleo'}`} aria-hidden />
      <div className="min-w-0 flex-1 text-[0.95rem]">
        {titulo && <p className="font-medium">{titulo}</p>}
        {children}
      </div>
      {accion}
    </div>
  )
}

export function Estado({ valor }) {
  const e = ESTADOS[valor] || { texto: valor, tono: 'neutro' }
  const clase = { ok: 'bg-petroleo-suave text-petroleo-oscuro', aviso: 'bg-aviso-suave text-aviso', grave: 'bg-grave-suave text-grave', neutro: 'bg-dom-0 text-grafito' }[e.tono]
  return <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-sm font-medium ${clase}`}>
    {(valor === 'procesando' || valor === 'en_cola') && <Loader2 size={13} className="animate-spin" aria-hidden />}{e.texto}</span>
}

export function Dominio({ puntaje, etiqueta }) {
  const n = nivelDominio(puntaje)
  return <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-sm font-medium"
    style={{ background: COLOR_DOMINIO[n.paso], color: TEXTO_DOMINIO[n.paso] }}>{etiqueta || n.etiqueta}</span>
}

/* La regla de 0 a 5: el elemento propio de la plataforma. Muestra dónde cae la nota
   (y, si se pasa, dónde estaba antes del ajuste) en vez de un número aislado. */
export function Regla({ nota, previa, grande = false, etiqueta }) {
  const pct = (v) => `${Math.min(Math.max(v, 0), 5) * 20}%`
  const tiene = nota !== null && nota !== undefined
  return (
    <div className={grande ? 'pt-9' : 'pt-7'} role="img" aria-label={tiene ? `${etiqueta || 'Nota'}: ${fmtNota(nota)} sobre 5,0` : 'Sin nota'}>
      <div className="relative h-3">
        <div className="absolute inset-x-0 top-1/2 h-px bg-tinta/70" />
        {Array.from({ length: 51 }, (_, i) => (
          <span key={i} className="absolute top-1/2 w-px -translate-x-1/2 bg-tinta/70"
            style={{ left: `${i * 2}%`, height: i % 10 === 0 ? 12 : i % 5 === 0 ? 8 : 4, marginTop: i % 10 === 0 ? -6 : i % 5 === 0 ? -4 : -2 }} />
        ))}
        <span className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-petroleo/25" style={{ left: '60%', right: 0 }} title="Zona de aprobación (3,0 o más)" />
        {previa !== null && previa !== undefined && previa !== nota && (
          <span className="absolute -top-1 h-5 w-0.5 -translate-x-1/2 bg-grafito/60" style={{ left: pct(previa) }} title={`Antes del ajuste: ${fmtNota(previa)}`} />
        )}
        {tiene && (
          <span className="absolute -translate-x-1/2" style={{ left: pct(nota), top: grande ? -38 : -30 }}>
            <span className={`num titulo block rounded-md bg-tinta px-2 font-bold text-white ${grande ? 'text-2xl py-0.5' : 'text-base'}`}>{fmtNota(nota)}</span>
            <span className="mx-auto block h-2.5 w-0.5 bg-tinta" />
          </span>
        )}
      </div>
      <div className="num mt-1.5 flex justify-between text-xs text-grafito" aria-hidden>
        {[0, 1, 2, 3, 4, 5].map((n) => <span key={n} className="w-0 whitespace-nowrap text-center" style={{ direction: 'ltr' }}><span className="-ml-1">{n}</span></span>)}
      </div>
    </div>
  )
}

export function Modal({ titulo, onCerrar, children, ancho = 'max-w-2xl' }) {
  const ref = useRef(null)
  useEffect(() => {
    const tecla = (e) => e.key === 'Escape' && onCerrar()
    document.addEventListener('keydown', tecla)
    ref.current?.focus()
    return () => document.removeEventListener('keydown', tecla)
  }, [onCerrar])
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-tinta/50 p-4 sm:p-8" onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}>
      <div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label={titulo} className={`w-full ${ancho} rounded-xl bg-white shadow-xl outline-none`}>
        <div className="flex items-center justify-between gap-4 border-b border-linea px-5 py-3.5">
          <h2 className="text-lg font-bold">{titulo}</h2>
          <button onClick={onCerrar} aria-label="Cerrar" className="rounded-md p-1.5 text-grafito hover:bg-papel"><X size={19} /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export function Cargando({ texto = 'Cargando' }) {
  return <p className="flex items-center gap-2 py-10 text-grafito"><Loader2 size={18} className="animate-spin" aria-hidden />{texto}…</p>
}

export function Vacio({ titulo, children, accion }) {
  return (
    <div className="rounded-xl border border-dashed border-linea bg-white/60 px-6 py-10 text-center">
      <p className="titulo text-lg font-bold">{titulo}</p>
      {children && <p className="mx-auto mt-1.5 max-w-xl text-grafito">{children}</p>}
      {accion && <div className="mt-4 flex justify-center">{accion}</div>}
    </div>
  )
}

export function Pagina({ titulo, bajada, acciones, children, migas }) {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-7 sm:px-8">
      {migas && <div className="mb-2 text-sm text-grafito">{migas}</div>}
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[1.75rem] font-bold sm:text-[2rem]">{titulo}</h1>
          {bajada && <p className="mt-1.5 max-w-3xl text-grafito">{bajada}</p>}
        </div>
        {acciones && <div className="no-imprimir flex flex-wrap gap-2">{acciones}</div>}
      </header>
      {children}
    </div>
  )
}

export function Seccion({ titulo, extra, children, className = '' }) {
  return (
    <section className={`rounded-xl border border-linea bg-white ${className}`}>
      {titulo && <div className="flex flex-wrap items-center justify-between gap-3 border-b border-linea px-5 py-3">
        <h2 className="text-lg font-bold">{titulo}</h2>{extra}</div>}
      <div className="p-5">{children}</div>
    </section>
  )
}

export function Lista({ items, vacio = 'Sin elementos.' }) {
  if (!items?.length) return <p className="text-grafito">{vacio}</p>
  return <ul className="list-disc space-y-1.5 pl-5 marker:text-petroleo">{items.map((t, i) => <li key={i}>{t}</li>)}</ul>
}

export function Pestanas({ opciones, valor, onCambio }) {
  return (
    <div role="tablist" className="no-imprimir mb-5 flex gap-1 overflow-x-auto border-b border-linea">
      {opciones.map(([id, texto, cuenta]) => (
        <button key={id} role="tab" aria-selected={valor === id} onClick={() => onCambio(id)}
          className={`-mb-px whitespace-nowrap border-b-2 px-3.5 py-2.5 font-medium ${valor === id ? 'border-petroleo text-petroleo-oscuro' : 'border-transparent text-grafito hover:text-tinta'}`}>
          {texto}{cuenta ? <span className="num ml-1.5 rounded-full bg-aviso-suave px-1.5 text-sm text-aviso">{cuenta}</span> : null}
        </button>
      ))}
    </div>
  )
}
