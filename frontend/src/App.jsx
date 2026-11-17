import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import Layout from './Layout.jsx'
import { Cargando } from './ui.jsx'
import Inicio from './pages/Inicio.jsx'
import Acceso from './pages/Acceso.jsx'
import Panel from './pages/Panel.jsx'
import Portafolio from './pages/Portafolio.jsx'
import Laboratorios from './pages/Laboratorios.jsx'
import Laboratorio from './pages/Laboratorio.jsx'
import RubricaEditor from './pages/RubricaEditor.jsx'
import Evaluacion from './pages/Evaluacion.jsx'
import Revision from './pages/Revision.jsx'
import Informe from './pages/Informe.jsx'
import Admin from './pages/Admin.jsx'

const Mapa = lazy(() => import('./pages/Mapa.jsx'))

function Privado({ children, docente, admin }) {
  const { usuario, cargando, esDocente, esAdmin } = useAuth()
  const ubicacion = useLocation()
  if (cargando) return <div className="p-8"><Cargando texto="Recuperando tu sesión" /></div>
  if (!usuario) return <Navigate to="/acceso" state={{ desde: ubicacion.pathname }} replace />
  if ((docente && !esDocente) || (admin && !esAdmin)) return <Navigate to="/app" replace />
  return <Layout>{children}</Layout>
}

export default function App() {
  return (
    <Suspense fallback={<div className="p-8"><Cargando /></div>}>
      <Routes>
        <Route path="/" element={<Inicio />} />
        <Route path="/acceso" element={<Acceso />} />
        <Route path="/app" element={<Privado><Panel /></Privado>} />
        <Route path="/app/portafolio" element={<Privado><Portafolio /></Privado>} />
        <Route path="/app/portafolio/:estudianteId" element={<Privado docente><Portafolio /></Privado>} />
        <Route path="/app/laboratorios" element={<Privado docente><Laboratorios /></Privado>} />
        <Route path="/app/laboratorios/:id" element={<Privado><Laboratorio /></Privado>} />
        <Route path="/app/rubricas/:id" element={<Privado docente><RubricaEditor /></Privado>} />
        <Route path="/app/evaluaciones/:id" element={<Privado><Evaluacion /></Privado>} />
        <Route path="/app/revision" element={<Privado docente><Revision /></Privado>} />
        <Route path="/app/informe" element={<Privado><Informe /></Privado>} />
        <Route path="/app/informe/:estudianteId" element={<Privado docente><Informe /></Privado>} />
        <Route path="/app/mapa" element={<Privado><Mapa /></Privado>} />
        <Route path="/app/mapa/:estudianteId" element={<Privado docente><Mapa /></Privado>} />
        <Route path="/app/admin" element={<Privado admin><Admin /></Privado>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
