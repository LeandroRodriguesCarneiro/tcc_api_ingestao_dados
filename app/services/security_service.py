import requests
from ..settings import Settings

class SecurityService:
    def __init__(self):

        self.auth_url = Settings.URL_API_AUTH.rstrip("/") + "/api/v1/User/me"

    def validate_access_token(self, token: str):

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(self.auth_url, headers=headers)

        if response.status_code != 200:
            raise Exception("Token inválido ou expirado")
        return True
