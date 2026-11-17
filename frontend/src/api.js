// Cliente de la API. El token se guarda en localStorage y viaja en la cabecera Authorization.
const CLAVE = 'asesor.token'

export const token = {
  leer: () => { try { return localStorage.getItem(CLAVE) || '' } catch { return '' } },
  guardar: (t) => { try { t ? localStorage.setItem(CLAVE, t) : localStorage.removeItem(CLAVE) } catch { /* modo privado */ } },
}

export class ErrorApi extends Error {
  constructor(mensaje, estado) { super(mensaje); this.estado = estado }
}

async function pedir(metodo, ruta, cuerpo, opciones = {}) {
  const cabeceras = {}
  const t = token.leer()
  if (t) cabeceras.Authorization = `Bearer ${t}`
  let body
  if (cuerpo instanceof FormData) body = cuerpo
  else if (cuerpo !== undefined) { cabeceras['Content-Type'] = 'application/json'; body = JSON.stringify(cuerpo) }
  let resp
  try {
    resp = await fetch(`/api${ruta}`, { method: metodo, headers: cabeceras, body })
  } catch {
    throw new ErrorApi('No hay conexión con el servidor. Si la plataforma estaba inactiva, puede tardar cerca de un minuto en despertar: vuelve a intentarlo.', 0)
  }
  if (resp.status === 401 && t && !opciones.sinRedirigir) {
    token.guardar('')
    window.dispatchEvent(new Event('asesor:sesion-vencida'))
  }
  if (!resp.ok) {
    let detalle = `Error ${resp.status}`
    try { const j = await resp.json(); detalle = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail) } catch { /* sin cuerpo */ }
    throw new ErrorApi(detalle, resp.status)
  }
  if (opciones.blob) return resp.blob()
  return resp.status === 204 ? null : resp.json()
}

export const api = {
  get: (r, o) => pedir('GET', r, undefined, o),
  post: (r, c, o) => pedir('POST', r, c, o),
  put: (r, c) => pedir('PUT', r, c),
  patch: (r, c) => pedir('PATCH', r, c),
  del: (r) => pedir('DELETE', r),
  // Descarga autenticada: el token nunca viaja en la URL.
  async descargar(ruta, nombre) {
    const blob = await pedir('GET', ruta, undefined, { blob: true })
    guardarBlob(blob, nombre)
  },
}

export function guardarBlob(blob, nombre) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = nombre
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

export const fmtNota = (n) => (n === null || n === undefined ? '—' : Number(n).toFixed(1).replace('.', ','))
export const fmtFecha = (iso) => (iso ? new Date(iso).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' }) : '')
export const fmtFechaHora = (iso) => (iso ? new Date(iso).toLocaleString('es-CO', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '')

export function nivelDominio(p) {
  if (p === null || p === undefined) return { etiqueta: 'Sin evidencia', paso: 0 }
  if (p >= 4.6) return { etiqueta: 'Superior', paso: 4 }
  if (p >= 4.0) return { etiqueta: 'Alto', paso: 3 }
  if (p >= 3.0) return { etiqueta: 'Básico', paso: 2 }
  return { etiqueta: 'Bajo', paso: 1 }
}
export const COLOR_DOMINIO = ['#e4e9e9', '#c3e4df', '#7fc5bc', '#2e8f87', '#0b4f4c']
export const TEXTO_DOMINIO = ['#12292e', '#12292e', '#12292e', '#ffffff', '#ffffff']

export const ESTADOS = {
  en_cola: { texto: 'En cola', tono: 'neutro' },
  procesando: { texto: 'Evaluando', tono: 'neutro' },
  preliminar: { texto: 'Preliminar · sin revisar', tono: 'aviso' },
  en_revision: { texto: 'En revisión docente', tono: 'aviso' },
  aprobada: { texto: 'Aprobada · sin publicar', tono: 'aviso' },
  publicada: { texto: 'Publicada', tono: 'ok' },
  error: { texto: 'Con error', tono: 'grave' },
  sin_evaluar: { texto: 'Sin evaluar', tono: 'neutro' },
}

// Lo que ve un estudiante de una evaluación que aún no puede abrir: en curso, con error o esperando al docente.
export const estadoOculto = (estado) => (['en_cola', 'procesando', 'error', 'publicada'].includes(estado) ? estado : 'en_revision')

const ACCIONES = {
  registro: 'Registro de cuenta', cambio_password: 'Cambio de contraseña', usuario_creado: 'Cuenta creada', usuario_modificado: 'Cuenta modificada',
  proyecto_editado: 'Presentación editada', config_ia_modificada: 'Modelo de IA modificado',
  laboratorio_creado: 'Laboratorio creado', laboratorio_modificado: 'Laboratorio modificado',
  rubrica_borrador_creado: 'Borrador de rúbrica creado', rubrica_ponderaciones_normalizadas: 'Ponderaciones normalizadas a 100 %', rubrica_validada: 'Rúbrica validada',
  entrega_creada: 'Entrega recibida', entrega_eliminada: 'Entrega eliminada',
  evaluacion_solicitada: 'Evaluación solicitada', evaluacion_generada: 'Evaluación generada', evaluacion_eliminada: 'Evaluación eliminada',
  evaluacion_aprobada: 'Evaluación aprobada', evaluacion_publicada: 'Evaluación publicada', evaluacion_reabierta: 'Evaluación reabierta',
  criterio_ajustado: 'Criterio ajustado por el docente', retroalimentacion_editada: 'Retroalimentación editada', informe_generado: 'Síntesis del informe generada',
}
export const fmtAccion = (a) => ACCIONES[a] || (a.charAt(0).toUpperCase() + a.slice(1)).replaceAll('_', ' ')
export const fmtNum = (n, d = 1) => (n === null || n === undefined ? '—' : Number(n).toLocaleString('es-CO', { maximumFractionDigits: d }))
