import logging

from googleapiclient.discovery import build

from .config import settings

logger = logging.getLogger(__name__)

HEADERS = ["Fecha", "Concepto", "Monto", "Banco", "Gmail ID"]


def get_service(creds):
    """Inicializa el servicio de Google Sheets API."""
    return build("sheets", "v4", credentials=creds)


def setup_headers(service):
    """Crea los headers en la primera fila si el sheet está vacío."""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=settings.google_sheet_id, range="A1:E1")
        .execute()
    )
    values = result.get("values", [])

    if not values or values[0] != HEADERS:
        service.spreadsheets().values().update(
            spreadsheetId=settings.google_sheet_id,
            range="A1:E1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()
        logger.info("Headers creados en el sheet")


def check_duplicate(service, message_id: str) -> bool:
    """Verifica si ya existe un registro con este Gmail message_id."""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=settings.google_sheet_id, range="E:E")
        .execute()
    )
    values = result.get("values", [])
    for row in values:
        if row and row[0] == message_id:
            logger.info(f"Duplicado encontrado para message_id: {message_id}")
            return True
    return False


def append_transaction(service, fecha: str, concepto: str, monto: float, banco: str, message_id: str):
    """Agrega una fila de transacción al sheet."""
    row = [fecha, concepto, monto, banco, message_id]
    service.spreadsheets().values().append(
        spreadsheetId=settings.google_sheet_id,
        range="A:E",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
    logger.info(f"Registrado en Sheet: {concepto} | {monto} | {banco}")
