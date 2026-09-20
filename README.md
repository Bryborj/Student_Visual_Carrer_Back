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
- 🔒 **Seguridad**: Hash de contraseñas con PBKDF2 sha512 (10,000 iteraciones, 64 bytes) 100% compatible con cuentas existentes, y hash SHA-256 anónimo para correos institucionales.
- 🐳 **Docker Compose**: Entorno de desarrollo local con PostgreSQL contenedorizado.

## Requisitos

- Python 3.12+ (o Docker)
- Docker & Docker Compose (opcional para desarrollo local)

## Inicio Rápido con Docker Compose (Recomendado)

1. Copia las variables de entorno:
   ```bash
   cp .env.example .env
   ```
2. Inicia los contenedores (PostgreSQL dev + FastAPI):
   ```bash
   docker compose up --build
   ```
3. Accede a la documentación interactiva en:
   - Swagger UI: `http://localhost:8001/docs`
   - ReDoc: `http://localhost:8001/redoc`

## Inicio Rápido Local (Sin Docker)

1. Crear y activar entorno virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecutar servidor de desarrollo:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Ejecutar Pruebas Automatizadas

```bash
pytest tests/ -v
```

---

## 👥 Trabajo Colaborativo

- **Si solo desarrollas Backend:** Clona este repositorio, ejecuta `docker compose up` o tu entorno virtual de Python, y prueba directamente en `http://localhost:8000/docs`.
- **Si trabajas en Fullstack:** Clona ambos repositorios (`Student_Visual_Carrer_Back` y `Student_Visual_Carrer_Front`) en una carpeta contenedora común para ejecutar ambos servicios simultáneamente.

