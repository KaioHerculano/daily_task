#!/bin/bash
set -e

echo "Aguardando banco de dados..."

: "${POSTGRES_HOST:=daily_task_db}"
: "${POSTGRES_PORT:=5432}"

# Verifica se nc está disponível
if ! command -v nc >/dev/null 2>&1; then
    echo "Erro: 'nc' (netcat) não está instalado."
    exit 1
fi

# Aguarda PostgreSQL ficar disponível
while ! nc -z -w 1 "$POSTGRES_HOST" "$POSTGRES_PORT"; do
    sleep 0.5
done

echo "Banco disponível."

case "$APP_ROLE" in

  web)
    echo "Aplicando migrations..."
    python manage.py migrate --noinput

    echo "Coletando arquivos estáticos..."
    python manage.py collectstatic --noinput

    echo "Ajustando permissões de mídia e estáticos..."
    mkdir -p /app/media/avatars /app/static
    chown -R root:root /app/media
    chmod -R 755 /app/media

    echo "Iniciando servidor web na porta 8002..."
    exec gunicorn app.wsgi:application --bind 0.0.0.0:8002
    ;;

  worker)
    echo "Iniciando Celery Worker..."

    : "${WORKER_NAME:=worker}"

    exec celery -A app worker \
        --loglevel=info \
        --concurrency=10 \
        --max-tasks-per-child=200 \
        --prefetch-multiplier=2 \
        --hostname="${WORKER_NAME}@%h"
    ;;

  beat)
    echo "Iniciando Celery Beat..."
    exec celery -A app beat --loglevel=info
    ;;

  *)
    echo "APP_ROLE inválido. Use: web, worker ou beat."
    exit 1
    ;;
esac
