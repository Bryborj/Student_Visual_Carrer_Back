# Student Visual Carrer - Backend (FastAPI) 🐺

Backend en Python y FastAPI para el visualizador de planes de estudio universitarios BUAP, sistema de foro y gobernanza estudiantil con aprobación por votos.

Este repositorio corresponde exclusivamente al **Backend**. El frontend complementario se encuentra en [Student_Visual_Carrer_Front](https://github.com/Bryborj/Student_Visual_Carrer_Front).

## Características

- 🚀 **FastAPI + Uvicorn**: API asíncrona de alto rendimiento con documentación OpenAPI interactiva (`/docs` y `/redoc`).
- 🐘 **PostgreSQL + asyncpg**: Pool de conexiones asíncrono para alto tráfico y transacciones atómicas.
- 🗳️ **Gobernanza y Votación Estudiantil**:
  - Los alumnos registrados pueden proponer cambios a los mapas curriculares.
  - Votación comunitaria estudiantil con cálculo de quórum.
  - Auto-aprobación y actualización del plan oficial en vivo cuando se alcanza la meta de votos.
  - Notificaciones automáticas por correo electrónico al staff/administradores cuando se aprueba una actualización.
- ✉️ **Resend API**: Envío de correos transaccionales (PINs OTP y alertas) desde `community@forobuap.zrootsh.com`.
- 🔒 **Seguridad**: Hash de contraseñas con PBKDF2 sha512 (10,000 iteraciones, 64 bytes) 100% compatible con cuentas existentes, y hash SHA-256 anónimo para correos institucionales. CORS restringido por `CORS_ORIGINS` y `ADMIN_PASSWORD` obligatoria fuera de `DEV_MODE`.
- 🐳 **Docker Compose**: Entorno de desarrollo local con PostgreSQL contenedorizado.

## Requisitos

- Python 3.12+ (o Docker)
- Docker & Docker Compose (opcional para desarrollo local)

## Entornos y variables

| Archivo | Uso | ¿Versionado? |
|---|---|---|
| `.env.example` | Plantilla de **desarrollo** (Postgres local) | Sí |
| `.env` | Tu copia local de desarrollo | No |
| `.env.prod.example` | Plantilla de **producción** | Sí |
| `.env.prod` | Valores reales de producción (BD remota, claves) | No |

- La BD de desarrollo es **siempre el Postgres local** del `docker-compose.yml` (`DATABASE_URL` fijado al servicio `postgres`).
- `DATABASE_URL` tiene prioridad sobre la variable legada `POSTGRES`.
- `.dockerignore` excluye cualquier `.env*` de la imagen: en producción inyecta las variables en el despliegue (`--env-file .env.prod` o el panel de tu plataforma).

## Inicio Rápido con Docker Compose (Recomendado)

1. Copia las variables de entorno:
   ```bash
   cp .env.example .env
   ```
2. Inicia los contenedores (PostgreSQL dev en `:5433` + FastAPI en `:8001`):
   ```bash
   docker compose up --build
   ```
3. Accede a la documentación interactiva en:
   - Swagger UI: `http://localhost:8001/docs`
   - ReDoc: `http://localhost:8001/redoc`
4. (Opcional) Carga los planes de estudio reales en tu BD local:
   ```bash
   export REMOTE_DATABASE_URL='postgresql://usuario:password@host:puerto/base'
   ./scripts/seed_dev.sh   # copia solo faculties y plans; nunca usuarios ni foro
   ```

## Inicio Rápido Local (Sin Docker)

1. Crear y activar entorno virtual:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Levantar solo la BD y ejecutar el servidor de desarrollo:
   ```bash
   docker compose up -d postgres
   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

## Ejecutar Pruebas Automatizadas

Las pruebas de integración usan un Postgres **real** y su propia base `forobuap_test` (se crea sola; nunca toca `forobuap_dev`).

```bash
docker compose up -d postgres
pytest -v          # TEST_DATABASE_URL por defecto: postgresql://postgres:devpassword@localhost:5433/forobuap_test
ruff check .
```

Si Postgres no está disponible, los tests de integración se omiten (`skipped`). El CI de GitHub Actions ejecuta `ruff` + `pytest` contra un servicio `postgres:16`.

## Notas de migración desde el monorepo

Este backend reemplaza al servidor Express de `Vizualizador_Plan_De_Estudios` (`/api/plans-list`, `/plan`, `/auth`, `/admin`, `/forum`, `/verifyEmail`, con las mismas `action`s), y añade `/api/proposals`. `api/bremo-otp.ts` (envío de PIN por Brevo) **no se portó**: no tenía referencias en el código y Resend lo sustituye.

---

## 👥 Trabajo Colaborativo

- **Si solo desarrollas Backend:** Clona este repositorio, ejecuta `docker compose up` o tu entorno virtual de Python, y prueba directamente en `http://localhost:8001/docs`.
- **Si trabajas en Fullstack:** Clona ambos repositorios (`Student_Visual_Carrer_Back` y `Student_Visual_Carrer_Front`) en una carpeta contenedora común para ejecutar ambos servicios simultáneamente.
