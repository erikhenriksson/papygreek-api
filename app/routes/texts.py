from starlette.routing import Route

from ..config import db
from ..response import JSONResponse

from . import analyses


async def get_text_dates():
    db_texts = await db.fetch_all(
        """
        SELECT CAST(NULLIF(date_not_before, '') AS SIGNED) AS date_not_before,
               CAST(NULLIF(date_not_after, '') AS SIGNED) AS date_not_after,
               id as text_id,
               (SELECT COUNT(*) FROM token WHERE token.text_id = text.id) as token_count
        FROM `text`
        """
    )
    return db_texts


async def get_text_dates_test(request):
    data = await get_text_dates()
    date_frequencies = analyses.get_text_date_frequencies(data["result"])

    return JSONResponse(date_frequencies)


async def get_texts_by_status(request):
    if request.path_params.get("status") == "update":
        db_texts = await db.fetch_all(
            """
            SELECT id, name, series_name, series_type, orig_status, reg_status 
              FROM `text` 
             WHERE `current` = 0
            """,
            request.path_params,
            natsort_by="name",
        )
    elif request.path_params.get("status") == "v1":
        db_texts = await db.fetch_all(
            """
            SELECT id, name, series_name, series_type, orig_status, reg_status 
              FROM `text` 
             WHERE v1 = 1
            """,
            request.path_params,
            natsort_by="name",
        )
    else:
        db_texts = await db.fetch_all(
            """
            SELECT id, name, series_name, series_type, orig_status, reg_status 
              FROM `text` 
             WHERE (orig_status IN (%(status)s) 
                OR reg_status IN (%(status)s))
            """,
            request.path_params,
            natsort_by="name",
        )
    return JSONResponse(db_texts)


async def get_texts_by_series(request):
    db_texts = await db.fetch_all(
        """
        SELECT id, name, tm, hgv, date_not_before, date_not_after, series_type, place_name, orig_status, reg_status 
          FROM `text` 
         WHERE series_name IN (%(series_name)s)
        """,
        request.path_params,
        natsort_by="name",
    )
    return JSONResponse(db_texts)


async def get_approved_texts(request):
    db_texts = await db.fetch_all(
        """
        SELECT id, name, series_name, series_type 
          FROM `text` 
         WHERE orig_status = 3 
           AND reg_status = 3 
         ORDER BY name 
        """,
        request.path_params,
        natsort_by="name",
    )
    return JSONResponse(db_texts)


routes = [
    Route("/approved", get_approved_texts),
    Route("/status/{status}", get_texts_by_status),
    Route("/series/{series_name}", get_texts_by_series),
    Route("/get_text_dates", get_text_dates_test),
]
