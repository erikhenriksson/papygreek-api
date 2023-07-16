from starlette.routing import Route

from ..config import db
from ..response import JSONResponse


def get_query(request):
    assert request.path_params["series_type"] in [
        "documentary",
        "inscriptions",
        "literary",
        "others",
    ]
    if request.path_params["series_type"] == "others":
        return f'NOT IN ("documentary", "inscriptions", "literary")'
    return f'IN ("{request.path_params["series_type"]}")'


async def get_series_by_type(request):
    q = get_query(request)
    result = await db.fetch_all(
        f"""
        SELECT DISTINCT series_name 
          FROM `text` 
         WHERE series_type {q}
    """,
        natsort_by="series_name",
    )
    return JSONResponse(result)


async def get_series_by_type_counts(request):
    q = get_query(request)
    result = await db.fetch_all(
        f"""
        SELECT DISTINCT series_name, 
               count(id) AS text_count 
          FROM `text` 
         WHERE series_type {q} 
         GROUP BY series_name
    """,
        natsort_by="series_name",
    )
    return JSONResponse(result)


routes = [
    Route("/type/{series_type}", get_series_by_type),
    Route("/type/{series_type}/counts", get_series_by_type_counts),
]
