#!/usr/bin/env bash
# Copia SOLO los planes de estudio (tablas faculties y plans) desde la BD remota hacia el Postgres local de desarrollo.
# NO copia usuarios, PINs, foro ni propuestas.
#
# Uso:
#   export REMOTE_DATABASE_URL='postgresql://usuario:password@host:puerto/base'
#   docker compose up -d --build        # la primera vez, para que el backend cree las tablas
#   ./scripts/seed_dev.sh
set -euo pipefail

cd "$(dirname "$0")/.."

: "${REMOTE_DATABASE_URL:?Define REMOTE_DATABASE_URL en tu shell (no se lee de ningún archivo .env).}"
LOCAL_USER="${POSTGRES_USER:-postgres}"
LOCAL_DB="${POSTGRES_DB:-forobuap_dev}"

echo "→ Verificando que las tablas locales existen..."
docker compose exec -T postgres psql -U "$LOCAL_USER" -d "$LOCAL_DB" -tAc \
  "SELECT to_regclass('public.plans') IS NOT NULL AND to_regclass('public.faculties') IS NOT NULL" | grep -q t \
  || { echo "Las tablas no existen. Levanta el backend una vez (docker compose up -d --build) y reintenta."; exit 1; }

echo "→ Copiando faculties y plans desde la BD remota..."
docker compose exec -T postgres pg_dump "$REMOTE_DATABASE_URL" \
    --data-only --no-owner --no-privileges --column-inserts --on-conflict-do-nothing \
    -t public.faculties -t public.plans \
  | docker compose exec -T postgres psql -U "$LOCAL_USER" -d "$LOCAL_DB" -v ON_ERROR_STOP=1 -q

docker compose exec -T postgres psql -U "$LOCAL_USER" -d "$LOCAL_DB" -tAc \
  "SELECT 'faculties: ' || count(*) FROM faculties UNION ALL SELECT 'plans: ' || count(*) FROM plans"
echo "✔ Listo."
