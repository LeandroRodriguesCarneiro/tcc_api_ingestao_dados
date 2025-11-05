import requests
from ..settings import Settings

class Security:
    def __init__(self, email: str = None, senha: str = None):

        self.auth_url = Settings.URL_API_AUTH.rstrip("/") + "/auth/me"

    def validate_access_token(self, token: str):

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(self.auth_url, headers=headers)

        if response.status_code != 200:
            raise Exception("Token inválido ou expirado")
        return True
