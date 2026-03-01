# Automatización de Gastos BCP/Interbank → Notion

## Problema
Los correos de notificación de BCP (Yape, transferencias, compras con tarjeta) e Interbank (tarjeta de crédito) llegan a Gmail. Se necesita extraer automáticamente los datos de cada transacción y registrarlos en Notion.

## Inspiración y referencias
- [**ethx42/ynab-gmail-integration**](https://github.com/ethx42/ynab-gmail-integration) — Gmail API + OpenAI para parsear notificaciones bancarias → YNAB. Misma arquitectura que usaremos pero con Notion en vez de YNAB.
- [**rakshran/expense-tracker**](https://github.com/rakshran/expense-tracker) — Gmail API + BeautifulSoup para scraping de emails de tarjetas de crédito y UPI. Usa labels de Gmail para categorizar antes de procesar, y BeautifulSoup para limpiar HTML antes de parsear. Adoptaremos ambas ideas.
- [**n8n template #9689**](https://n8n.io/workflows/9689) — Patrón de deduplicación: busca en Notion por ID antes de crear, para evitar duplicados. Implementaremos lo mismo.

## Datos clave descubiertos
- **BCP** envía notificaciones desde `notificaciones@bcp.com.pe`
- **Yape** permite configurar notificaciones por correo para yapeos desde S/10, S/50, S/100 o S/500
- **Interbank** envía alertas de consumo de tarjeta de crédito (remitente por confirmar)
- Los correos son HTML con tablas — usaremos BeautifulSoup para limpiar antes de enviar a la IA (ahorra tokens)

## Arquitectura
```
Cron/Scheduler
     ↓
Gmail API (OAuth2)
     ↓
Filtrar: from:(notificaciones@bcp.com.pe OR alertas@interbank.com.pe) AND -label:gastos-procesado
     ↓
BeautifulSoup (limpiar HTML → texto)
     ↓
Gemini 2.5 Flash Lite (structured output → JSON)
     ↓
Notion API (crear página en database)
     ↓
Gmail API (etiquetar como "gastos-procesado")
```

## Stack técnico
- **Python 3.11+** con `uv` como package manager (moderno, rápido)
- **google-api-python-client** + **google-auth-oauthlib** — Gmail API OAuth2
- **beautifulsoup4** — limpiar HTML de emails (reducir tokens antes de IA)
- **google-genai** — SDK oficial de Google Generative AI para Gemini 2.5 Flash Lite (barato, rápido, structured output con JSON mode)
- **notion-client** — SDK oficial de Notion
- **pydantic** — modelos de datos validados para transacciones
- **python-dotenv** — variables de entorno
- **schedule** (opcional) — scheduler interno alternativo a cron

## Estructura del proyecto
```
Gastos_yape_interbank/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point — orquesta el flujo completo
│   ├── gmail_client.py      # Gmail API: buscar, leer, etiquetar correos
│   ├── email_parser.py      # BeautifulSoup + Gemini para extraer datos
│   ├── notion_client.py     # Notion API: crear registros, verificar duplicados
│   ├── models.py            # Pydantic models: Transaction, EmailData
│   └── config.py            # Settings con pydantic-settings desde .env
├── .env.example
├── .gitignore
├── pyproject.toml           # Config con uv
├── setup_gmail.py           # Helper one-time para OAuth2
├── Dockerfile               # Para despliegue en VPS
├── docker-compose.yml       # Compose con cron interno
└── README.md
```

## Componentes detallados

### 1. Modelos de datos (`models.py`)
Usaremos Pydantic para validar la estructura de transacciones:
- `Transaction`: monto (float), moneda (PEN/USD), tipo (Yape/Transferencia/Compra TC/Pago), comercio_o_destinatario (str), fecha_hora (datetime), banco (BCP/Interbank), ultimos_4_digitos (str|None), categoria (str), descripcion_original (str)
- `EmailData`: message_id (str), subject (str), sender (str), date (datetime), body_text (str)

### 2. Gmail Client (`gmail_client.py`)
- `get_service()` — inicializar Gmail API con OAuth2, auto-refresh de token
- `get_or_create_label(name)` — crear label "gastos-procesado" si no existe
- `fetch_unprocessed_emails()` — query: `from:(notificaciones@bcp.com.pe OR <interbank_sender>) -label:gastos-procesado` con límite configurable
- `get_email_content(msg_id)` → `EmailData` — extraer subject, body HTML/text, fecha
- `mark_as_processed(msg_id)` — agregar label "gastos-procesado"

### 3. Email Parser (`email_parser.py`)
- `clean_html(html)` → str — BeautifulSoup para extraer texto limpio, eliminar estilos/scripts
- `parse_transaction(email_data: EmailData)` → `Transaction` — envía texto limpio a Gemini 2.5 Flash Lite con prompt estructurado y response_mime_type="application/json" + response_schema del modelo Pydantic
- Prompt incluye contexto de bancos peruanos: BCP, Interbank, Yape, soles (S/), tipos de operación
- Categorías predefinidas: Alimentación, Transporte, Entretenimiento, Compras, Servicios, Salud, Educación, Transferencia, Otros

### 4. Notion Client (`notion_client.py`)
- `create_transaction(transaction: Transaction)` — crear página en database con propiedades mapeadas
- `check_duplicate(message_id: str)` → bool — buscar por message_id de Gmail para evitar duplicados
- Mapeo de propiedades:
  - Comercio/Destinatario → Title
  - Monto → Number
  - Moneda → Select (PEN/USD)
  - Tipo → Select (Yape/Transferencia/Compra TC/Pago)
  - Banco → Select (BCP/Interbank)
  - Categoría → Select
  - Fecha → Date
  - Últimos 4 dígitos → Rich text
  - Gmail Message ID → Rich text (para deduplicación)
  - Descripción original → Rich text

### 5. Flujo principal (`main.py`)
1. Cargar config
2. Conectar Gmail API
3. Buscar correos no procesados
4. Por cada correo:
   a. Extraer contenido → `EmailData`
   b. Verificar duplicado en Notion (por message_id)
   c. Limpiar HTML + parsear con IA → `Transaction`
   d. Crear registro en Notion
   e. Etiquetar correo como procesado en Gmail
   f. Log del resultado
5. Resumen: "Procesados X correos, Y errores"

### 6. Manejo de errores
- Si falla el parseo IA: loguear y saltar (no marcar como procesado)
- Si falla Notion: loguear y saltar (no marcar como procesado)
- Solo marcar como procesado si TODO el pipeline fue exitoso
- Retry con backoff para errores de API (rate limits)

## Despliegue en VPS

**Opción A: Docker (recomendada)**
- `docker-compose up -d` — corre con cron interno cada 15 min
- El token OAuth2 se persiste en un volume

**Opción B: Cron directo**
- `pip install -e .` en el VPS
- Cron: `*/15 * * * * cd /path/to/project && python -m src.main >> /var/log/gastos.log 2>&1`

## Prerequisitos del usuario
1. Google Cloud Console: proyecto con Gmail API habilitada + credenciales OAuth2 tipo Desktop → descargar `credentials.json`
2. Notion: Integration creada en https://www.notion.so/my-integrations → copiar token. Database de gastos creada con las propiedades listadas arriba y conectada a la integration.
3. Google AI Studio: API key de Gemini desde https://aistudio.google.com/apikey
4. Confirmar el email exacto del remitente de Interbank (revisar un correo de notificación)

## Skills recomendadas para instalar
```bash
npx skills add composiohq/awesome-claude-skills@gmail-automation -g -y
npx skills add intellectronica/agent-skills@notion-api -g -y
```
