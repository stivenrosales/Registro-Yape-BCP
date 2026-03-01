import base64
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .config import settings
from .models import EmailData

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_credentials():
    """Obtiene credenciales OAuth2 compartidas (Gmail + Sheets)."""
    creds = None
    token_path = Path(settings.gmail_token_path)
    credentials_path = Path(settings.gmail_credentials_path)

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return creds


def get_service(creds=None):
    """Inicializa el servicio de Gmail API con OAuth2."""
    if creds is None:
        creds = get_credentials()
    return build("gmail", "v1", credentials=creds)


def get_or_create_label(service, label_name: str) -> str:
    """Obtiene o crea un label en Gmail. Retorna el label ID."""
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    label_body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=label_body).execute()
    logger.info(f"Label '{label_name}' creado con ID: {created['id']}")
    return created["id"]


def fetch_unprocessed_emails(service) -> list[dict]:
    """Busca correos de BCP/Yape/Interbank no procesados."""
    senders = " OR ".join(s.strip() for s in settings.email_senders.split(","))
    query = f"from:({senders}) -label:{settings.gmail_processed_label} after:{settings.emails_after_date} -ward"
    logger.info(f"Buscando correos con query: {query}")

    messages = []
    result = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=settings.max_emails_per_run)
        .execute()
    )
    messages.extend(result.get("messages", []))

    logger.info(f"Encontrados {len(messages)} correos sin procesar")
    return messages


def get_email_content(service, msg_id: str) -> EmailData:
    """Extrae el contenido de un correo de Gmail."""
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = msg["payload"]["headers"]

    subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "")
    sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "")
    date_str = next((h["value"] for h in headers if h["name"].lower() == "date"), "")

    try:
        date = parsedate_to_datetime(date_str)
    except Exception:
        date = datetime.now(timezone.utc)

    body_html = _extract_body(msg["payload"])

    return EmailData(
        message_id=msg_id,
        subject=subject,
        sender=sender,
        date=date,
        body_text=body_html,
    )


def _extract_body(payload: dict) -> str:
    """Extrae el cuerpo HTML (o texto) del payload del correo."""
    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result

    return ""


def mark_as_processed(service, msg_id: str, label_id: str):
    """Agrega el label 'gastos-procesado' al correo."""
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"addLabelIds": [label_id]},
    ).execute()
    logger.info(f"Correo {msg_id} marcado como procesado")
