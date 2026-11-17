import { useRef, useState } from 'react'
import { Camera, KeyRound, Plus, PlugZap, RefreshCw, Save, Trash2, UserPlus } from 'lucide-react'
import { api, fmtAccion, fmtFecha, fmtFechaHora } from '../api'
import { useAuth } from '../auth.jsx'
import { Aviso, Boton, Campo, Cargando, Modal, Pagina, Pestanas, Seccion, useDatos } from '../ui.jsx'

const ROLES = { admin: 'Administración', docente: 'Docente', estudiante: 'Estudiante' }

/* ---------- Usuarios ---------- */

function FormularioUsuario({ onListo, onCancelar }) {
  const [f, setF] = useState({ nombre: '', email: '', password: '', rol: 'estudiante', codigo: '' })
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const cambiar = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const enviar = async (e) => {
    e.preventDefault(); setOcupado(true); setError('')
    try { await api.post('/usuarios', f); onListo() } catch (err) { setError(err.message); setOcupado(false) }
  }
  return (
    <form onSubmit={enviar} className="space-y-4">
      <Campo etiqueta="Nombre completo"><input className="campo" required minLength={3} value={f.nombre} onChange={cambiar('nombre')} /></Campo>
      <div className="grid gap-4 sm:grid-cols-2">
        <Campo etiqueta="Correo"><input className="campo" type="email" required value={f.email} onChange={cambiar('email')} /></Campo>
        <Campo etiqueta="Rol"><select className="campo" value={f.rol} onChange={cambiar('rol')}>{Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Campo>
        <Campo etiqueta="Contraseña inicial" ayuda="Mínimo 8 caracteres, con letras y números."><input className="campo" required minLength={8} value={f.password} onChange={cambiar('password')} autoComplete="new-password" /></Campo>
        <Campo etiqueta="Código estudiantil (opcional)"><input className="campo" value={f.codigo} onChange={cambiar('codigo')} /></Campo>
      </div>
      {error && <Aviso tono="grave">{error}</Aviso>}
      <div className="flex justify-end gap-2"><Boton type="button" variante="secundario" onClick={onCancelar}>Cancelar</Boton><Boton type="submit" ocupado={ocupado}>Crear cuenta</Boton></div>
    </form>
  )
}

function Usuarios() {
  const { usuario: yo } = useAuth()
  const { datos, error, cargando, recargar } = useDatos(() => api.get('/usuarios'))
  const [creando, setCreando] = useState(false)
  const [clave, setClave] = useState(null) // usuario al que se le restablece la contraseña
  const [nueva, setNueva] = useState('')
  const [fallo, setFallo] = useState('')
  const cambiar = async (u, cambios) => {
    setFallo('')
    try { await api.patch(`/usuarios/${u.id}`, cambios); await recargar(true) } catch (e) { setFallo(e.message) }
  }
  if (cargando) return <Cargando />
  if (error) return <Aviso tono="grave">{error}</Aviso>
  return (
    <Seccion titulo={`Cuentas (${datos.length})`} extra={<Boton icono={UserPlus} onClick={() => setCreando(true)}>Crear cuenta</Boton>}>
      {fallo && <div className="mb-4"><Aviso tono="grave">{fallo}</Aviso></div>}
      <div className="overflow-x-auto">
        <table className="tabla w-full">
          <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Alta</th><th>Estado</th><th className="text-right">Acciones</th></tr></thead>
          <tbody>
            {datos.map((u) => (
              <tr key={u.id} className={u.activo ? '' : 'text-grafito'}>
                <td className="font-medium">{u.nombre}{u.codigo && <span className="block text-sm font-normal text-grafito">Código {u.codigo}</span>}</td>
                <td>{u.email}</td>
                <td>
                  <select aria-label={`Rol de ${u.nombre}`} className="campo !w-auto !py-1" value={u.rol} disabled={u.id === yo.id} onChange={(e) => cambiar(u, { rol: e.target.value })}>
                    {Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </td>
                <td className="whitespace-nowrap text-grafito">{fmtFecha(u.creado_en)}</td>
                <td>{u.activo ? 'Activa' : 'Desactivada'}</td>
                <td className="text-right">
                  <button className="block w-full whitespace-nowrap text-right font-medium text-petroleo underline" onClick={() => { setClave(u); setNueva(''); setFallo('') }}>Cambiar contraseña</button>
                  {u.id !== yo.id && <button className="mt-1 block w-full whitespace-nowrap text-right font-medium text-petroleo underline" onClick={() => cambiar(u, { activo: !u.activo })}>{u.activo ? 'Desactivar' : 'Reactivar'}</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {creando && <Modal titulo="Crear cuenta" onCerrar={() => setCreando(false)}><FormularioUsuario onCancelar={() => setCreando(false)} onListo={() => { setCreando(false); recargar(true) }} /></Modal>}
      {clave && (
        <Modal titulo={`Restablecer contraseña de ${clave.nombre}`} onCerrar={() => setClave(null)} ancho="max-w-md">
          <form className="space-y-4" onSubmit={async (e) => { e.preventDefault(); try { await api.patch(`/usuarios/${clave.id}`, { password: nueva }); setClave(null) } catch (err) { setFallo(err.message) } }}>
            <Campo etiqueta="Nueva contraseña" ayuda="Mínimo 8 caracteres, con letras y números. Entrégala por un canal seguro.">
              <input className="campo" required minLength={8} value={nueva} onChange={(e) => setNueva(e.target.value)} autoComplete="new-password" />
            </Campo>
            {fallo && <Aviso tono="grave">{fallo}</Aviso>}
            <div className="flex justify-end gap-2"><Boton type="button" variante="secundario" onClick={() => setClave(null)}>Cancelar</Boton><Boton type="submit" icono={KeyRound}>Guardar contraseña</Boton></div>
          </form>
        </Modal>
      )}
    </Seccion>
  )
}

/* ---------- Proyecto y equipo ---------- */

const LISTAS = [['objetivos', 'Objetivos'], ['funcionalidades', 'Funcionalidades'], ['tecnologias', 'Tecnologías utilizadas'], ['aportes', 'Aportes del proyecto']]

function Integrante({ persona, onCambio }) {
  const [f, setF] = useState(persona)
  const [estado, setEstado] = useState('')
  const [error, setError] = useState('')
  const archivo = useRef(null)
  const cambiar = (k) => (e) => { setF({ ...f, [k]: e.target.value }); setEstado('') }
  const guardar = async () => {
    setError('')
    try {
      await api.patch(`/proyecto/integrantes/${persona.id}`, { nombre: f.nombre, rol: f.rol, descripcion: f.descripcion, enlace: f.enlace, orden: Number(f.orden) || 1 })
      setEstado('Guardado'); onCambio()
    } catch (e) { setError(e.message) }
  }
  const subir = async (e) => {
    const foto = e.target.files?.[0]
    if (!foto) return
    setError('')
    const cuerpo = new FormData(); cuerpo.append('foto', foto)
    try { const r = await api.post(`/proyecto/integrantes/${persona.id}/foto`, cuerpo); setF((a) => ({ ...a, foto: r.foto })); onCambio() } catch (err) { setError(err.message) }
    e.target.value = ''
  }
  return (
    <li className="grid gap-4 py-5 sm:grid-cols-[7rem_1fr]">
      <div>
        {f.foto
          ? <img src={f.foto} alt={`Fotografía de ${f.nombre}`} className="h-28 w-28 rounded-xl object-cover" />
          : <div className="flex h-28 w-28 items-center justify-center rounded-xl border border-dashed border-linea bg-papel text-center text-sm text-grafito">Sin fotografía</div>}
        <input ref={archivo} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={subir} />
        <button onClick={() => archivo.current.click()} className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-petroleo underline"><Camera size={15} aria-hidden />{f.foto ? 'Cambiar foto' : 'Subir foto'}</button>
      </div>
      <div className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_5rem]">
          <Campo etiqueta="Nombre"><input className="campo" value={f.nombre} onChange={cambiar('nombre')} /></Campo>
          <Campo etiqueta="Rol en el equipo"><input className="campo" value={f.rol} onChange={cambiar('rol')} /></Campo>
          <Campo etiqueta="Orden"><input className="campo" type="number" min="1" value={f.orden} onChange={cambiar('orden')} /></Campo>
        </div>
        <Campo etiqueta="Aporte al proyecto"><textarea className="campo !min-h-16" value={f.descripcion} onChange={cambiar('descripcion')} /></Campo>
        <Campo etiqueta="Enlace (GitHub o LinkedIn, opcional)"><input className="campo" type="url" placeholder="https://" value={f.enlace} onChange={cambiar('enlace')} /></Campo>
        {error && <Aviso tono="grave">{error}</Aviso>}
        <div className="flex items-center gap-3">
          <Boton variante="secundario" icono={Save} onClick={guardar}>Guardar integrante</Boton>
          <Boton variante="peligro" icono={Trash2} onClick={async () => { if (window.confirm(`¿Quitar a ${f.nombre} del equipo?`)) { await api.del(`/proyecto/integrantes/${persona.id}`); onCambio() } }}>Quitar</Boton>
          {estado && <span className="text-sm text-petroleo-oscuro" role="status">{estado}</span>}
        </div>
      </div>
    </li>
  )
}

function Proyecto() {
  const { datos, error, cargando, recargar } = useDatos(async () => {
    const [p, pub] = await Promise.all([api.get('/proyecto'), api.get('/publico/proyecto')])
    return { p, equipo: pub.equipo }
  })
  const [f, setF] = useState(null)
  const [estado, setEstado] = useState('')
  const [fallo, setFallo] = useState('')
  if (cargando) return <Cargando />
  if (error) return <Aviso tono="grave">{error}</Aviso>
  const v = f || { ...datos.p, ...Object.fromEntries(LISTAS.map(([k]) => [k, (datos.p[k] || []).join('\n')])) }
  const cambiar = (k) => (e) => { setF({ ...v, [k]: e.target.value }); setEstado('') }
  const guardar = async () => {
    setFallo('')
    try {
      await api.put('/proyecto', { titulo: v.titulo, lema: v.lema, institucion: v.institucion, abstract: v.abstract,
        ...Object.fromEntries(LISTAS.map(([k]) => [k, v[k].split('\n').map((s) => s.trim()).filter(Boolean)])) })
      setEstado('Cambios guardados. Ya se ven en la página de inicio.')
    } catch (e) { setFallo(e.message) }
  }
  return (
    <div className="space-y-6">
      <Seccion titulo="Presentación del proyecto" extra={<Boton icono={Save} onClick={guardar}>Guardar presentación</Boton>}>
        <div className="space-y-4">
          {estado && <Aviso tono="ok">{estado}</Aviso>}
          {fallo && <Aviso tono="grave">{fallo}</Aviso>}
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo etiqueta="Título"><input className="campo" value={v.titulo} onChange={cambiar('titulo')} /></Campo>
            <Campo etiqueta="Lema"><input className="campo" value={v.lema} onChange={cambiar('lema')} /></Campo>
          </div>
          <Campo etiqueta="Institución y asignatura"><input className="campo" value={v.institucion} onChange={cambiar('institucion')} /></Campo>
          <Campo etiqueta="Abstract"><textarea className="campo !min-h-36" value={v.abstract} onChange={cambiar('abstract')} /></Campo>
          <div className="grid gap-4 lg:grid-cols-2">
            {LISTAS.map(([k, etiqueta]) => <Campo key={k} etiqueta={etiqueta} ayuda="Un elemento por línea."><textarea className="campo !min-h-32" value={v[k]} onChange={cambiar(k)} /></Campo>)}
          </div>
        </div>
      </Seccion>
      <Seccion titulo="Equipo desarrollador" extra={<Boton variante="secundario" icono={Plus} onClick={async () => { await api.post('/proyecto/integrantes', { nombre: 'Nuevo integrante', rol: '', orden: datos.equipo.length + 1 }); recargar(true) }}>Agregar integrante</Boton>}>
        <p className="text-grafito">Fotografía, nombre y rol de cada integrante aparecen en la página pública de inicio. Fotos JPG, PNG o WebP de hasta 3 MB.</p>
        <ul className="divide-y divide-linea">{datos.equipo.map((i) => <Integrante key={i.id} persona={i} onCambio={() => recargar(true)} />)}</ul>
      </Seccion>
    </div>
  )
}

/* ---------- Modelo de IA ---------- */

function ModeloIA() {
  const { datos, error, cargando, fijar } = useDatos(() => api.get('/config/ia'))
  const [f, setF] = useState(null)
  const [clave, setClave] = useState('')
  const [prueba, setPrueba] = useState(null)
  const [modelos, setModelos] = useState(null)
  const [ocupado, setOcupado] = useState('')
  const [fallo, setFallo] = useState('')
  if (cargando) return <Cargando />
  if (error) return <Aviso tono="grave">{error}</Aviso>
  const v = f || datos
  const prov = datos.proveedores.find((p) => p.id === v.proveedor)
  const cambiarProveedor = (id) => {
    const p = datos.proveedores.find((x) => x.id === id)
    const mismo = id === datos.proveedor
    setF({ ...v, proveedor: id, modelo: mismo ? datos.modelo : p.modelo_sugerido, base_url: mismo ? datos.base_url : p.base_url, temperatura: mismo ? datos.temperatura : null })
    setPrueba(null); setModelos(null); setClave('')
  }
  const guardar = async (extra = {}) => {
    setOcupado('guardar'); setFallo('')
    try {
      const r = await api.put('/config/ia', { proveedor: v.proveedor, modelo: v.modelo, base_url: v.base_url,
        temperatura: v.temperatura === '' || v.temperatura === null ? null : Number(v.temperatura), multimodal: v.multimodal,
        pasadas_consistencia: Number(v.pasadas_consistencia) || 1, api_key: clave, ...extra })
      fijar(r); setF(null); setClave(''); setPrueba({ ok: true, mensaje: 'Configuración guardada. Las próximas evaluaciones usarán este modelo.' })
      return true
    } catch (e) { setFallo(e.message); return false } finally { setOcupado('') }
  }
  const probar = async () => {
    if ((f || clave) && !(await guardar())) return
    setOcupado('probar'); setPrueba(null)
    try { setPrueba(await api.post('/config/ia/probar')) } catch (e) { setPrueba({ ok: false, mensaje: e.message }) } finally { setOcupado('') }
  }
  const listar = async () => {
    if ((f || clave) && !(await guardar())) return
    setOcupado('listar')
    try { setModelos((await api.get('/config/ia/modelos')).modelos) } catch (e) { setFallo(e.message) } finally { setOcupado('') }
  }
  const mismoGuardado = v.proveedor === datos.proveedor
  return (
    <div className="grid gap-6 lg:grid-cols-[1.3fr_.7fr]">
      <Seccion titulo="Conexión con el modelo">
        <div className="space-y-4">
          {datos.proveedor === 'simulado' && <Aviso tono="aviso" titulo="Modo simulado activo">Las evaluaciones se generan con reglas heurísticas, sin modelo de IA. Sirve para recorrer la plataforma, no para calificar. Elige un proveedor y guarda su clave para evaluar de verdad.</Aviso>}
          <Campo etiqueta="Proveedor">
            <select className="campo" value={v.proveedor} onChange={(e) => cambiarProveedor(e.target.value)}>{datos.proveedores.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select>
          </Campo>
          {v.proveedor !== 'simulado' && <>
            <Campo etiqueta="Modelo" ayuda={prov.modelo_sugerido ? `Sugerido: ${prov.modelo_sugerido}. Debe admitir salida estructurada (JSON).` : 'Escribe el identificador exacto del modelo. Debe admitir salida estructurada (JSON).'}>
              <div className="flex gap-2">
                <input className="campo" list="modelos-ia" value={v.modelo} onChange={(e) => setF({ ...v, modelo: e.target.value })} spellCheck={false} />
                <Boton variante="secundario" icono={RefreshCw} ocupado={ocupado === 'listar'} onClick={listar} className="shrink-0">Ver disponibles</Boton>
              </div>
              <datalist id="modelos-ia">{(modelos || []).map((m) => <option key={m} value={m} />)}</datalist>
            </Campo>
            {modelos && <p className="text-sm text-grafito">{modelos.length ? `${modelos.length} modelos disponibles con esta clave: empieza a escribir en el campo para elegir uno.` : 'El proveedor no devolvió modelos.'}</p>}
            <Campo etiqueta="URL base" ayuda={v.proveedor === 'ollama' ? 'Dirección del servidor Ollama, alcanzable desde el servidor de la plataforma.' : 'Cámbiala solo si usas un servicio compatible o un proxy.'}>
              <input className="campo" value={v.base_url} onChange={(e) => setF({ ...v, base_url: e.target.value })} spellCheck={false} />
            </Campo>
            {prov.requiere_clave && (
              <Campo etiqueta="Clave de API" ayuda={mismoGuardado && datos.clave_configurada ? `Hay una clave guardada (${datos.origen_clave}${datos.clave_pista ? `, termina en ${datos.clave_pista}` : ''}). Escribe otra solo para reemplazarla.` : 'Se guarda cifrada en la base de datos y nunca vuelve al navegador.'}>
                <input className="campo" type="password" value={clave} onChange={(e) => setClave(e.target.value)} autoComplete="off" placeholder={mismoGuardado && datos.clave_configurada ? '••••••••' : ''} />
              </Campo>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo etiqueta="Temperatura" ayuda="Vacío = valor recomendado para el proveedor.">
                <input className="campo" type="number" min="0" max="2" step="0.1" value={v.temperatura ?? ''} onChange={(e) => setF({ ...v, temperatura: e.target.value })} />
              </Campo>
              <Campo etiqueta="Pasadas de consistencia" ayuda="Con 2 o 3, cada criterio se valora varias veces y se marca para revisión si discrepan. Multiplica el costo.">
                <select className="campo" value={v.pasadas_consistencia} onChange={(e) => setF({ ...v, pasadas_consistencia: e.target.value })}>{[1, 2, 3].map((n) => <option key={n}>{n}</option>)}</select>
              </Campo>
            </div>
            <label className="flex items-start gap-2.5">
              <input type="checkbox" className="mt-1 h-4 w-4 accent-[#0b6e69]" checked={v.multimodal} onChange={(e) => setF({ ...v, multimodal: e.target.checked })} />
              <span>Enviar imágenes y diagramas al modelo<span className="block text-sm text-grafito">Usa visión para las figuras del informe y las presentaciones. Desactívalo si el modelo es solo de texto.</span></span>
            </label>
          </>}
          {fallo && <Aviso tono="grave">{fallo}</Aviso>}
          {prueba && <Aviso tono={prueba.ok ? 'ok' : 'grave'} titulo={prueba.ok ? undefined : 'La prueba falló'}>{prueba.mensaje}{prueba.modelo && prueba.uso ? ` Modelo: ${prueba.modelo}.` : ''}</Aviso>}
          <div className="flex flex-wrap gap-2">
            <Boton icono={Save} ocupado={ocupado === 'guardar'} onClick={() => guardar()}>Guardar configuración</Boton>
            <Boton variante="secundario" icono={PlugZap} ocupado={ocupado === 'probar'} onClick={probar}>Guardar y probar conexión</Boton>
            {mismoGuardado && datos.origen_clave === 'administración' && <Boton variante="peligro" onClick={() => guardar({ borrar_api_key: true })}>Borrar clave guardada</Boton>}
          </div>
        </div>
      </Seccion>
      <Seccion titulo="Cómo se usa el modelo">
        <ul className="list-disc space-y-2.5 pl-5 marker:text-petroleo">
          <li>El modelo elige un nivel de la rúbrica por criterio y cita la evidencia. La nota la calcula el servidor con las ponderaciones.</li>
          <li>La respuesta se valida contra un esquema; si no cumple, se reintenta y, si sigue sin cumplir, la evaluación queda con error en vez de inventar un resultado.</li>
          <li>Cada evaluación guarda el proveedor, el modelo y la temperatura con que se hizo.</li>
          <li>Si la misma entrega se evalúa con la misma rúbrica y el mismo modelo, se reutiliza el resultado anterior.</li>
          <li>Costos, límites y requisitos de cada proveedor están en <span className="font-medium">docs/MODELOS_IA.md</span>.</li>
        </ul>
      </Seccion>
    </div>
  )
}

/* ---------- Sistema ---------- */

function Sistema() {
  const { datos, error, cargando, recargar } = useDatos(async () => {
    const [sistema, auditoria, proyecto, cohortes] = await Promise.all([api.get('/config/sistema'), api.get('/auditoria?limite=150'), api.get('/proyecto'), api.get('/cohortes')])
    return { sistema, auditoria, proyecto, cohortes }
  })
  const [fallo, setFallo] = useState('')
  if (cargando) return <Cargando />
  if (error) return <Aviso tono="grave">{error}</Aviso>
  const s = datos.sistema
  const filas = [
    ['Modelo de IA', `${s.ia.proveedor} · ${s.ia.modelo} (clave: ${s.ia.clave})`],
    ['Sandbox de código', s.sandbox.habilitado ? `Activo · ${s.sandbox.tiempo_s} s de reloj, ${s.sandbox.cpu_s} s de CPU, ${s.sandbox.memoria_mb} MB, red ${s.sandbox.red}` : 'Desactivado: solo se hace análisis sin ejecutar código'],
    ['Base de datos', s.base_datos], ['Entorno', `${s.entorno} · Python ${s.python}`],
    ['Registro de estudiantes', s.registro_abierto ? 'Abierto' : 'Cerrado: las cuentas las crea el docente'],
    ['Totales', `${s.totales.usuarios} cuentas · ${s.totales.entregas} entregas · ${s.totales.evaluaciones} evaluaciones`],
  ]
  const guardarCohorte = async (c, cambios) => {
    setFallo('')
    try { await api.patch(`/cohortes/${c.id}`, { numero: c.numero, nombre: c.nombre, periodo: c.periodo || '', descripcion: c.descripcion || '', ...cambios }); recargar(true) } catch (e) { setFallo(e.message) }
  }
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Seccion titulo="Estado del sistema">
          <dl className="divide-y divide-linea">{filas.map(([k, val]) => <div key={k} className="grid gap-1 py-2.5 sm:grid-cols-[11rem_1fr]"><dt className="text-grafito">{k}</dt><dd>{val}</dd></div>)}</dl>
        </Seccion>
        <div className="space-y-6">
          <Seccion titulo="Publicación de resultados">
            <label className="flex items-start gap-2.5">
              <input type="checkbox" className="mt-1 h-4 w-4 accent-[#0b6e69]" checked={Boolean(datos.proyecto.estudiante_ve_preliminar)}
                onChange={async (e) => { await api.put('/proyecto', { estudiante_ve_preliminar: e.target.checked }); recargar(true) }} />
              <span>Mostrar al estudiante la evaluación preliminar<span className="block text-sm text-grafito">Por defecto el estudiante solo ve una evaluación cuando el docente la aprueba y la publica. Si lo activas, verá la valoración de la IA marcada como «preliminar, sin revisión docente».</span></span>
            </label>
          </Seccion>
          <Seccion titulo="Cohortes">
            {fallo && <div className="mb-3"><Aviso tono="grave">{fallo}</Aviso></div>}
            <ul className="space-y-3">
              {datos.cohortes.map((c) => (
                <li key={c.id} className="grid gap-3 sm:grid-cols-[1fr_9rem]">
                  <Campo etiqueta={`Nombre de la cohorte ${c.numero}`}><input className="campo" defaultValue={c.nombre} onBlur={(e) => e.target.value.trim() !== c.nombre && guardarCohorte(c, { nombre: e.target.value.trim() })} /></Campo>
                  <Campo etiqueta="Periodo"><input className="campo" defaultValue={c.periodo || ''} placeholder="2026-2" onBlur={(e) => e.target.value.trim() !== (c.periodo || '') && guardarCohorte(c, { periodo: e.target.value.trim() })} /></Campo>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-sm text-grafito">Los cambios se guardan al salir de cada campo.</p>
          </Seccion>
        </div>
      </div>
      <Seccion titulo="Registro de auditoría" extra={<span className="text-sm text-grafito">Últimas {datos.auditoria.length} acciones</span>}>
        {datos.auditoria.length === 0 ? <p className="text-grafito">Aún no hay acciones registradas.</p> : (
          <div className="max-h-[28rem] overflow-auto">
            <table className="tabla w-full">
              <thead><tr><th>Cuándo</th><th>Quién</th><th>Acción</th><th>Sobre</th><th>Detalle</th></tr></thead>
              <tbody>
                {datos.auditoria.map((a) => (
                  <tr key={a.id}>
                    <td className="whitespace-nowrap text-grafito">{fmtFechaHora(a.creado_en)}</td>
                    <td>{a.usuario}</td>
                    <td>{fmtAccion(a.accion)}</td>
                    <td className="whitespace-nowrap text-grafito">{a.entidad}{a.entidad_id ? ` n.º ${a.entidad_id}` : ''}</td>
                    <td className="text-sm text-grafito">{a.detalle && Object.keys(a.detalle).length ? Object.entries(a.detalle).map(([k, val]) => `${k}: ${Array.isArray(val) ? val.join(', ') : typeof val === 'object' && val !== null ? JSON.stringify(val) : val}`).join(' · ') : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Seccion>
    </div>
  )
}

export default function Admin() {
  const [pestana, setPestana] = useState('usuarios')
  return (
    <Pagina titulo="Administración" bajada="Cuentas, presentación pública del proyecto, modelo de IA y estado del sistema.">
      <Pestanas valor={pestana} onCambio={setPestana} opciones={[['usuarios', 'Usuarios'], ['proyecto', 'Proyecto y equipo'], ['ia', 'Modelo de IA'], ['sistema', 'Sistema y auditoría']]} />
      {pestana === 'usuarios' && <Usuarios />}
      {pestana === 'proyecto' && <Proyecto />}
      {pestana === 'ia' && <ModeloIA />}
      {pestana === 'sistema' && <Sistema />}
    </Pagina>
  )
}
