# Despliegue

La aplicación es una sola imagen Docker (frontend compilado + API) más una base de datos PostgreSQL.

## Render (recomendado para la entrega)

1. Sube el proyecto a un repositorio de GitHub.
2. En https://dashboard.render.com: **New → Blueprint** y elige el repositorio. Render lee `render.yaml` y propone un servicio web y una base de datos.
3. Completa lo que pide:
   - `ADMIN_EMAIL`: el correo del administrador.
   - `ADMIN_PASSWORD`: mínimo 8 caracteres, con letras y números.
   - `GEMINI_API_KEY`: la clave de Google AI Studio. Puede quedar vacía y configurarse después dentro de la plataforma.
4. **Apply**. La primera compilación tarda unos minutos. La URL pública queda en la página del servicio.
5. Entra con la cuenta de administrador y haz la lista de comprobación de abajo.

`SECRET_KEY` la genera Render. No la cambies después: firma las sesiones y cifra la clave de API guardada; si cambia, hay que iniciar sesión otra vez y volver a guardar la clave.

Plan gratuito: el servicio se duerme tras un rato sin visitas y la siguiente tarda cerca de un minuto en responder. Abre la URL unos minutos antes de la sustentación. La base de datos gratuita tiene fecha de vencimiento: revísala en el panel.

## Lista de comprobación después de publicar

1. Abre la URL: debe verse la página de inicio con el resumen del proyecto y el equipo.
2. Entra como administrador → **Administración → Modelo de IA**: elige el proveedor, pega la clave y usa «Guardar y probar conexión». Debe responder «El modelo respondió y la salida cumple el esquema».
3. **Administración → Proyecto y equipo**: escribe nombre, rol y aporte de cada integrante y sube las fotografías.
4. **Administración → Sistema y auditoría**: la base de datos debe decir PostgreSQL y el sandbox, activo.
5. Entra como docente, abre una entrega y usa «Evaluar de nuevo» para tener al menos una evaluación hecha con el modelo real. En su pestaña Verificación técnica revisa que las capas del sandbox aparezcan activas.
6. Cambia las contraseñas de las cuentas de demostración o desactívalas si la plataforma va a recibir datos reales (`SEED_DEMO=false` evita crearlas).

## Cualquier servidor con Docker

```bash
docker build -t asesor .
docker run -d -p 80:8000 \
  -e SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  -e DATABASE_URL="postgresql://usuario:clave@host:5432/asesor" \
  -e ADMIN_EMAIL=admin@ejemplo.edu.co -e ADMIN_PASSWORD='UnaClaveLarga2026' \
  -e IA_PROVEEDOR=gemini -e GEMINI_API_KEY=... \
  asesor
```

Sin `DATABASE_URL` usa SQLite dentro del contenedor: monta un volumen en `/app/backend/data` para no perder los datos. Pon HTTPS delante (el proxy del proveedor, Caddy o nginx). `--build-arg SANDBOX_EXTRAS=true` añade pandas, scikit-learn y matplotlib para las pruebas de los estudiantes.

Railway, Fly.io o Koyeb funcionan igual: imagen Docker, las mismas variables y el puerto de `PORT`.

## Variables

Están descritas en `.env.example`. Las mínimas en producción: `SECRET_KEY`, `DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

## Notas de operación

- Un solo proceso web. Las evaluaciones corren en hilos de ese proceso; si el servicio se reinicia a mitad de una, queda marcada con error y se puede volver a pedir.
- Las tablas se crean al arrancar. No hay migraciones: un cambio de esquema posterior requiere agregarlas (Alembic) o recrear la base.
- Si el alojamiento no permite seccomp, el sandbox sigue funcionando con las demás capas y la evaluación lo deja registrado.
