from starlette.config import Config
from .db import db

env = Config(".env")

DEBUG = env("DEBUG", cast=bool, default=False)
PREFIX = env("PREFIX", default="")
JWT_SECRET = env("JWT_SECRET")
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")

DB_USER = env("DB_USER")
DB_HOST = env("DB_HOST", default="localhost")
DB_PORT = env("DB_PORT", default=3306)
DB_PASSWORD = env("DB_PASSWORD")
DB_DB = env("DB_DB")
BACKUP_DIR = env("BACKUP_DIR", default="~/backups")

ZOTERO_URL = env("ZOTERO_URL")
SMYTH_PATH = env("SMYTH_PATH")
IDP_PATH = env("IDP_PATH")

db = db()
