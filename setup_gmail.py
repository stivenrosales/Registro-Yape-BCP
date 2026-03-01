"""
Helper para configurar OAuth2 de Gmail por primera vez.

Uso:
    python setup_gmail.py

Prerequisitos:
    1. Descargar credentials.json de Google Cloud Console
    2. Colocarlo en la raíz del proyecto

Esto abrirá el navegador para autorizar la app y generará token.json.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
]


def setup():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)

    with open("token.json", "w") as f:
        f.write(creds.to_json())

    print("Token guardado en token.json")
    print("Ya puedes ejecutar: python -m src.main")


if __name__ == "__main__":
    setup()
