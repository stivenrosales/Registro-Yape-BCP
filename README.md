# Registro Automático de Gastos BCP/Yape

Automatiza el registro de tus transacciones bancarias BCP y Yape en Google Sheets. Lee los correos de notificación de Gmail, extrae los datos con IA y los registra automáticamente.

```
Gmail (BCP/Yape) → BeautifulSoup → Gemini AI → Google Sheets
```

## Cómo funciona

1. **Busca** correos no procesados de `notificaciones@notificacionesbcp.com.pe` y `notificaciones@yape.pe`
2. **Filtra** correos a partir de una fecha configurable y excluye operaciones de wardadito
3. **Limpia** el HTML del correo con BeautifulSoup para extraer el texto relevante
4. **Extrae** los datos de la transacción con Gemini 2.5 Flash Lite via OpenRouter (concepto, monto, banco, fecha)
5. **Registra** la transacción en Google Sheets (gastos en negativo, ingresos en positivo)
6. **Etiqueta** el correo como `gastos-procesado` para no volver a procesarlo

### Tipos de transacciones soportadas

| Tipo | Ejemplo | Signo |
|------|---------|-------|
| Compra con tarjeta | HIPERMERCADO TOTTUS | -25.50 |
| Yapeo enviado | Yapeo a Juan Pérez | -50.00 |
| Yapeo recibido | Yapeo de María López | +100.00 |
| Transferencia | Transferencia a terceros BCP | -750.00 |
| Pago de servicios | Pago ELECTROcentro | -116.20 |
| PLIN | PLIN-Luis Rosales | -200.00 |
| Recarga celular | Recarga Yape Integratel | -5.00 |
| Devolución | Devolución YAPE | +8.00 |

### Correos excluidos

- Operaciones de **wardadito** (cualquier correo que contenga "ward" en asunto o cuerpo)

## Requisitos previos

### 1. Google Cloud Console
- Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com/)
- Habilita **Gmail API** y **Google Sheets API**
- Crea credenciales OAuth2 tipo **Desktop** y descarga `credentials.json`

### 2. Google Sheet
- Crea un Google Sheet (o usa uno existente)
- Copia el ID del sheet desde la URL: `https://docs.google.com/spreadsheets/d/{ESTE_ES_EL_ID}/edit`

### 3. OpenRouter
- Obtén tu API key en [openrouter.ai/keys](https://openrouter.ai/keys)

## Instalación local

```bash
# Clonar el repositorio
git clone https://github.com/stivenrosales/Registro-Yape-BCP.git
cd Registro-Yape-BCP

# Instalar dependencias
uv sync

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Autorizar Gmail (abre el navegador, solo la primera vez)
uv run python setup_gmail.py

# Ejecutar
uv run python -m src.main
```

## Despliegue en VPS (EasyPanel / Docker)

El Dockerfile incluye un scheduler que ejecuta el pipeline cada 15 minutos.

### Variables de entorno requeridas

| Variable | Descripción |
|----------|-------------|
| `OPENROUTER_API_KEY` | API key de OpenRouter |
| `GOOGLE_SHEET_ID` | ID del Google Sheet |
| `GMAIL_CREDENTIALS_B64` | `credentials.json` codificado en base64 |
| `GMAIL_TOKEN_B64` | `token.json` codificado en base64 |

### Variables de entorno opcionales

| Variable | Default | Descripción |
|----------|---------|-------------|
| `EMAIL_SENDERS` | `notificaciones@notificacionesbcp.com.pe,notificaciones@yape.pe` | Remitentes a monitorear (separados por coma) |
| `EMAILS_AFTER_DATE` | `2026/03/01` | Solo procesar correos a partir de esta fecha |
| `GEMINI_MODEL` | `google/gemini-2.5-flash-lite` | Modelo de IA en OpenRouter |
| `MAX_EMAILS_PER_RUN` | `50` | Máximo de correos por ejecución |
| `GMAIL_PROCESSED_LABEL` | `gastos-procesado` | Label de Gmail para correos procesados |

Para generar los valores base64:

```bash
base64 -i credentials.json
base64 -i token.json
```

### Docker Compose

```bash
docker compose up -d
```

### EasyPanel

1. Crear servicio **App** desde GitHub → `stivenrosales/Registro-Yape-BCP`
2. Agregar las variables de entorno en la configuración
3. Deploy — no necesita puerto ni dominio, es un worker en background

## Stack

- **Python 3.12** con **uv**
- **Gmail API** — lectura y etiquetado de correos
- **Google Sheets API** — registro de transacciones
- **BeautifulSoup** — limpieza de HTML (reduce tokens antes de enviar a la IA)
- **Gemini 2.5 Flash Lite** via **OpenRouter** — extracción estructurada de datos
- **Pydantic** — validación de datos

## Estructura

```
src/
├── main.py           # Orquestador del pipeline
├── gmail_client.py   # Gmail API: buscar, leer, etiquetar
├── email_parser.py   # BeautifulSoup + Gemini para extraer datos
├── sheets_client.py  # Google Sheets: registrar transacciones
├── models.py         # Modelos Pydantic (Transaction, EmailData)
└── config.py         # Settings desde .env
```

## Configuración

### Agregar más remitentes

Edita `EMAIL_SENDERS` en tu `.env` separando por comas:

```env
EMAIL_SENDERS=notificaciones@notificacionesbcp.com.pe,notificaciones@yape.pe,otro@banco.com
```

### Cambiar fecha de inicio

Para procesar correos desde otra fecha:

```env
EMAILS_AFTER_DATE=2026/01/01
```
