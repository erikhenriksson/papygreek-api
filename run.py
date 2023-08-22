import sys
import asyncio

import uvicorn
from starlette.config import Config

from app.textmanager import texts, variations, closures, backup, morpheus
from app.config import db

env = Config(".env")

SSH_KEY = env("SSH_KEY", default="")
SSH_CERT = env("SSHCERT", default="")
IDP_PATH = env("IDP_PATH", default="")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=5000,
            log_level="info",
            ssl_keyfile="./localhost+2-key.pem",
            ssl_certfile="./localhost+2.pem",
            reload=True,
        )
    else:
        flags = sys.argv[2:] if len(sys.argv) > 2 else []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(db.connect())
        if "debug" in flags:
            loop.run_until_complete(db.set_debug())
        if sys.argv[1] == "update_texts":
            loop.run_until_complete(texts.cli(flags))
        elif sys.argv[1] == "update_variations":
            loop.run_until_complete(variations.cli())
        elif sys.argv[1] == "update_closures":
            loop.run_until_complete(closures.cli())
        elif sys.argv[1] == "backup_database":
            loop.run_until_complete(backup.cli())
        elif sys.argv[1] == "index_morpheus":
            loop.run_until_complete(morpheus.cli())
        loop.run_until_complete(db.disconnect())
