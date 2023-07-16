import jwt

from starlette.authentication import (
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
    AuthCredentials,
)

from . import config


class GoogleUser(BaseUser):
    def __init__(self, email: str, name: str, level: int, id: int) -> None:
        self.email = email
        self.name = name
        self.level = level
        self.id = id


class JWTAuthBackend(AuthenticationBackend):
    async def authenticate(self, request):
        if "authorization" not in request.headers:
            return

        auth = request.headers["authorization"]

        _, credentials = auth.split()
        try:
            decoded = jwt.decode(
                credentials,
                config.JWT_SECRET,
                algorithms=["HS256"],
                audience=config.GOOGLE_CLIENT_ID,
                options={"verify_exp": False},
            )
        except:
            raise AuthenticationError("Invalid JWT token")
        credentials = decoded["level"]
        return AuthCredentials(credentials), GoogleUser(
            decoded["email"], decoded["name"], decoded["level"], decoded["id"]
        )
