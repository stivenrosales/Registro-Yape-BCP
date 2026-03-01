import json
import logging

from bs4 import BeautifulSoup
from openai import OpenAI

from .config import settings
from .models import EmailData, Transaction

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres un asistente que extrae datos de transacciones bancarias de correos electrónicos peruanos.

Contexto:
- BCP y su billetera Yape envían notificaciones de operaciones (yapeos, transferencias, compras con tarjeta)
- Interbank envía alertas de consumo de tarjeta de crédito
- La moneda principal es Soles (PEN), simbolizada con "S/". También puede haber operaciones en USD.

Tu trabajo es extraer los datos de la transacción y devolver un JSON con esta estructura exacta:
{
  "concepto": "<nombre del comercio, persona o concepto breve>",
  "monto": <float con signo>,
  "banco": "BCP" o "Interbank",
  "fecha": "YYYY-MM-DD"
}

Reglas para el monto:
- Si es un GASTO (compra, pago, transferencia enviada, yapeo enviado): monto NEGATIVO (ej: -25.50)
- Si es un INGRESO (transferencia recibida, yapeo recibido, abono): monto POSITIVO (ej: 100.00)
- Si el correo dice "recibiste" o "te enviaron" o "abono" → es ingreso (positivo)
- Si el correo dice "compraste" o "pagaste" o "enviaste" o "consumo" → es gasto (negativo)

Reglas generales:
- El concepto debe ser corto y claro (nombre del comercio o persona)
- La fecha en formato YYYY-MM-DD
- Responde SOLO con el JSON, sin texto adicional"""


def clean_html(html: str) -> str:
    """Limpia HTML de correo y extrae texto relevante."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["style", "script", "head", "meta", "link"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def parse_transaction(email_data: EmailData) -> Transaction:
    """Parsea un correo de transacción bancaria usando Gemini via OpenRouter."""
    clean_text = clean_html(email_data.body_text)

    user_message = (
        f"Asunto: {email_data.subject}\n"
        f"De: {email_data.sender}\n"
        f"Fecha del correo: {email_data.date.isoformat()}\n\n"
        f"Contenido:\n{clean_text}"
    )

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )

    response = client.chat.completions.create(
        model=settings.gemini_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    logger.debug(f"Respuesta IA: {raw}")

    data = json.loads(raw)
    transaction = Transaction(**data)

    logger.info(f"Parseado: {transaction.concepto} | {transaction.monto} | {transaction.banco}")
    return transaction
