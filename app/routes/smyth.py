from starlette.routing import Route
from ..response import JSONResponse

from ..config import SMYTH_PATH


async def get_smyth_page(request):
    q = await request.json()
    html = ""
    with open(f'{SMYTH_PATH}/xhtml/{q["page"]}', "r") as file:
        html = file.read()
    return JSONResponse({"ok": True, "result": html})


async def get_smyth_css(request):
    css_list = []
    files = ["tei.css"]
    for f in files:
        with open(f"{SMYTH_PATH}/xhtml/{f}", "r") as file:
            css_list.append(file.read())
    css = '<style type="text/css">' + "\n".join(css_list) + "</style>"
    return JSONResponse({"ok": True, "result": css})


routes = [
    Route("/get_page", get_smyth_page, methods=["POST"]),
    Route("/get_css", get_smyth_css),
]
