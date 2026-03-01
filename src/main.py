import logging
import sys

from . import gmail_client, email_parser, sheets_client
from .config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Inicio de procesamiento de gastos ===")

    # Obtener credenciales compartidas (Gmail + Sheets)
    creds = gmail_client.get_credentials()

    # Conectar servicios
    gmail = gmail_client.get_service(creds)
    sheets = sheets_client.get_service(creds)
    label_id = gmail_client.get_or_create_label(gmail, settings.gmail_processed_label)

    # Asegurar headers en el sheet
    sheets_client.setup_headers(sheets)

    # Buscar correos no procesados
    messages = gmail_client.fetch_unprocessed_emails(gmail)

    if not messages:
        logger.info("No hay correos nuevos para procesar")
        return

    processed = 0
    errors = 0

    for msg in messages:
        msg_id = msg["id"]
        try:
            # Extraer contenido del correo
            email_data = gmail_client.get_email_content(gmail, msg_id)
            logger.info(f"Procesando: {email_data.subject}")

            # Verificar duplicado
            if sheets_client.check_duplicate(sheets, msg_id):
                gmail_client.mark_as_processed(gmail, msg_id, label_id)
                logger.info(f"Duplicado, marcando como procesado: {msg_id}")
                continue

            # Parsear transacción con IA
            transaction = email_parser.parse_transaction(email_data)

            # Registrar en Google Sheets
            sheets_client.append_transaction(
                sheets,
                fecha=transaction.fecha,
                concepto=transaction.concepto,
                monto=transaction.monto,
                banco=transaction.banco,
                message_id=msg_id,
            )

            # Marcar como procesado en Gmail
            gmail_client.mark_as_processed(gmail, msg_id, label_id)
            processed += 1

        except Exception:
            logger.exception(f"Error procesando correo {msg_id}")
            errors += 1

    logger.info(f"=== Resumen: {processed} procesados, {errors} errores ===")


if __name__ == "__main__":
    main()
