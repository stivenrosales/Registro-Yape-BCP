#!/bin/sh
set -e

# Decodificar credenciales desde variables de entorno (base64)
if [ -n "$GMAIL_CREDENTIALS_B64" ]; then
    echo "$GMAIL_CREDENTIALS_B64" | base64 -d > /app/credentials.json
fi

if [ -n "$GMAIL_TOKEN_B64" ]; then
    echo "$GMAIL_TOKEN_B64" | base64 -d > /app/token.json
fi

# Ejecutar el scheduler
exec python -c "
import schedule, time, logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('scheduler')

from src.main import main

schedule.every(15).minutes.do(main)
logger.info('Scheduler iniciado — ejecutando cada 15 minutos')
main()  # Ejecutar inmediatamente al iniciar
while True:
    schedule.run_pending()
    time.sleep(60)
"
