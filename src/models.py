from datetime import datetime

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    concepto: str = Field(description="Comercio, persona o concepto de la transacción")
    monto: float = Field(description="Monto con signo: negativo si es gasto, positivo si es ingreso")
    banco: str = Field(description="Banco: BCP o Interbank")
    fecha: str = Field(description="Fecha de la transacción en formato YYYY-MM-DD")


class EmailData(BaseModel):
    message_id: str = Field(description="ID del mensaje en Gmail")
    subject: str = Field(description="Asunto del correo")
    sender: str = Field(description="Remitente del correo")
    date: datetime = Field(description="Fecha del correo")
    body_text: str = Field(description="Cuerpo del correo en texto plano")
