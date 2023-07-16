import requests
import json

from starlette.routing import Route
from ..response import JSONResponse
from starlette.authentication import requires

from ..config import db, ZOTERO_URL


async def get_zotero_library():
    response = requests.get(ZOTERO_URL)
    try:
        if response.status_code == 200:
            return response.json()
    except:
        return


async def get_library(request):
    library = await db.fetch_one(
        """
        SELECT data 
          FROM bibliography
        """
    )
    return JSONResponse(json.loads(library["result"]["data"]))


@requires("editor")
async def update_library(request):
    if library := await get_zotero_library():
        lib_items = library["items"]
        for i, k in enumerate(lib_items):
            if "note" in k:
                try:
                    lib_items[i]["id"] = k["note"].split("Key:")[1].strip()
                except:
                    pass

        lib_dump = json.dumps(lib_items)

        result = await db.execute(
            """
            INSERT INTO bibliography (id, data) 
            VALUES (1, %(library)s) 
            ON DUPLICATE KEY UPDATE data = %(library)s
            """,
            {"library": lib_dump},
        )

        return JSONResponse(result)

    return JSONResponse(
        {"ok": False, "result": "Error fetching library"}, status_code=403
    )


routes = [Route("/update_library", update_library), Route("/get_library", get_library)]
