"""
   Overriding Starlette's own JSONResponse 
"""

from typing import Any
import json
from starlette.responses import JSONResponse as DefaultJSONResponse


class JSONResponse(DefaultJSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=str,  # This line was added (datetime fix)
        ).encode("utf-8")
