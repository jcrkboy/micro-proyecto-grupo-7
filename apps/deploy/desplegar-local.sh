#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 0 ]]; then
  echo "Uso: bash apps/deploy/desplegar-local.sh" >&2
  exit 2
fi
cd -- "$(dirname -- "$0")"
export API_IMAGE=sleep-edfx-api:local
export WEB_IMAGE=sleep-edfx-web:local
export WEB_HOST_PORT="127.0.0.1:${LOCAL_WEB_PORT:-8081}"

# Compose resuelve variables del entorno y del .env sin ejecutar su contenido como Bash.
modelos=$(docker compose config --environment | sed -n 's/^MODELOS_HOST_DIR=//p')
modelos=${modelos:-../../modelos}
for archivo in manifest.json dart.txt crnn.keras; do
  if [[ ! -f "$modelos/$archivo" || ! -s "$modelos/$archivo" || ! -r "$modelos/$archivo" ]]; then
    echo "Se necesita un archivo legible con contenido en $modelos/$archivo." >&2
    exit 1
  fi
done

docker build -t "$API_IMAGE" -f ../api/Dockerfile ../..
docker build -t "$WEB_IMAGE" ../web

# La API carga los pesos al arrancar, incluso si solo cambió el contenido del montaje.
docker compose up -d --pull never --force-recreate --wait
echo "Abre http://$WEB_HOST_PORT"
