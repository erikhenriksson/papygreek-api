from starlette.routing import Route
from starlette.authentication import requires
from ..response import JSONResponse

from ..config import db
from ..utils import is_int, cols


async def get_aow_person(aow_person_id):
    return await db.fetch_one(
        """    
        SELECT aow_n, 
               aow_person.id AS id, 
               person_id, 
               role, 
               handwriting, 
               honorific, 
               ethnic, 
               occupation, 
               domicile, 
               age, 
               education, 
               name, 
               tm_id, 
               uncertain, 
               gender
          FROM aow_person
               LEFT JOIN person
               ON aow_person.person_id = person.id
         WHERE aow_person.id = %(id)s
        """,
        {"id": aow_person_id},
    )


async def get_aows_by_text_id(request):
    q = await request.json()
    metadata = []
    aows = await db.fetch_all(
        """
            SELECT aow_n, 
                   hand
              FROM token
             WHERE text_id = %(id)s
               AND aow_n > 0
             GROUP BY aow_n
             ORDER BY aow_n
        """,
        {"id": q["text_id"]},
    )

    for aow in aows["result"]:
        metadatum = {
            "aow_n": aow["aow_n"],
            "hand": aow["hand"],
            "text_types": [],
            "people": [],
        }

        text_types = await db.fetch_all(
            """
                SELECT aow_n, 
                       text_type, 
                       id, 
                       hypercategory, 
                       category, 
                       subcategory, 
                       status
                  FROM aow_text_type
                 WHERE text_id = %(id)s
                   AND aow_n = %(aow_n)s
                 ORDER BY aow_n, id
        """,
            {"id": q["text_id"], "aow_n": aow["aow_n"]},
        )

        if text_types["ok"]:
            metadatum["text_types"] = text_types["result"]

        people = await db.fetch_all(
            """    
                SELECT aow_n, 
                       aow_person.id AS id, 
                       person_id, 
                       role, 
                       handwriting, 
                       honorific, 
                       ethnic, 
                       occupation, 
                       domicile, 
                       age, 
                       education, 
                       name, 
                       tm_id, 
                       uncertain, 
                       gender
                  FROM aow_person
                       LEFT JOIN person
                       ON aow_person.person_id = person.id
                 WHERE text_id = %(id)s
                   AND aow_n = %(aow_n)s 
              ORDER BY aow_n, id
        """,
            {"id": q["text_id"], "aow_n": aow["aow_n"]},
        )

        if people["ok"]:
            metadatum["people"] = people["result"]

        metadata.append(metadatum)

    return JSONResponse({"ok": True, "result": metadata})


@requires("editor")
async def add_aow_text_type(request):
    q = await request.json()
    cat = [0, 0, 0]
    for i, c in enumerate(q["text_type"].split("-")):
        cat[i] += int(c)

    result = await db.execute(
        """
        INSERT INTO aow_text_type (text_id, aow_n, hypercategory, category, subcategory, `status`) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (q["text_id"], q["aow_n"], cat[0], cat[1], cat[2], q["status"]),
    )
    if result["ok"]:
        new_aow_tt = await db.fetch_one(
            """
            SELECT * 
              FROM aow_text_type 
             WHERE id = %(id)s
        """,
            {"id": result["result"]},
        )
        return JSONResponse(new_aow_tt)


@requires("editor")
async def delete_aow_text_type(request):
    q = await request.json()
    result = await db.execute(
        """
        DELETE 
          FROM aow_text_type 
         WHERE id = %s
    """,
        (q["aow_tt_id"],),
    )

    if result["ok"]:
        return JSONResponse({"ok": True})


@requires("editor")
async def add_aow_person(request):
    q = await request.json()
    result = await db.execute(
        """
        INSERT INTO aow_person (text_id, aow_n, person_id, role) 
        VALUES (%s, %s, %s, %s)
    """,
        (q["text_id"], q["aow_n"], 912, "author"),
    )
    if result["ok"]:
        return JSONResponse(await get_aow_person(result["result"]))
    else:
        print(result)
        return JSONResponse({"ok": False, "result": "Please refresh the page"})


@requires("editor")
async def delete_aow_person(request):
    q = await request.json()
    result = await db.execute(
        """
        DELETE 
          FROM aow_person 
         WHERE id = %s
    """,
        (q["aow_person_id"],),
    )

    return JSONResponse(result)


@requires("editor")
async def update_aow_person_uncertainty(request):
    q = await request.json()
    result = await db.execute(
        """
        UPDATE aow_person 
           SET uncertain = %(uncertain)s 
         WHERE id = %(id)s
    """,
        ({"id": q["aow_person_id"], "uncertain": q["uncertain"]}),
    )

    return JSONResponse(result)


@requires("editor")
async def update_aow_person_id(request):
    q = await request.json()
    result = await db.execute(
        """
        UPDATE aow_person 
           SET person_id = %(person_id)s 
         WHERE id = %(id)s
    """,
        ({"person_id": q["person_id"], "id": q["aow_person_id"]}),
    )
    if result["ok"]:
        return JSONResponse(await get_aow_person(q["aow_person_id"]))
    else:
        return JSONResponse({"ok": False})


@requires("editor")
async def add_person_and_association(request):
    q = await request.json()
    tm_id = q["tm_id"] if is_int(q["tm_id"]) else None
    gender = q["gender"] if is_int(q["gender"]) else None
    result = await db.execute(
        """
        INSERT INTO person (name, tm_id, gender) 
        VALUES (%s, %s, %s)
    """,
        (q["person_name"], tm_id, q["gender"]),
    )
    if result["ok"]:
        result = await db.execute(
            """
            UPDATE aow_person 
               SET person_id = %(person_id)s 
             WHERE id = %(id)s
        """,
            ({"person_id": result["result"], "id": q["aow_person_id"]}),
        )
        if result["ok"]:
            return JSONResponse(await get_aow_person(q["aow_person_id"]))
    else:
        print(result)
    return JSONResponse({"ok": False})


@requires("editor")
async def update_aow_person_detail(request):
    q = await request.json()
    assert q["item"] in cols("aow_person")
    result = await db.execute(
        f"""
        UPDATE aow_person 
           SET {q['item']} = %(value)s 
         WHERE id = %(id)s
    """,
        ({"value": q["value"], "id": q["aow_person_id"]}),
    )
    if result["ok"]:
        return JSONResponse({"ok": True, "result": ""})


@requires("editor")
async def update_aow_person_role(request):
    q = await request.json()
    result = await db.execute(
        """
        UPDATE aow_person 
           SET role = %(role)s 
         WHERE id = %(id)s
    """,
        ({"role": q["role"], "id": q["aow_person_id"]}),
    )
    if result["ok"]:
        return JSONResponse({"ok": True, "result": ""})


routes = [
    Route("/", get_aows_by_text_id, methods=["POST"]),
    Route("/add_aow_text_type", add_aow_text_type, methods=["POST"]),
    Route("/add_aow_person", add_aow_person, methods=["POST"]),
    Route("/delete_aow_text_type", delete_aow_text_type, methods=["POST"]),
    Route("/delete_aow_person", delete_aow_person, methods=["POST"]),
    Route(
        "/update_aow_person_uncertainty",
        update_aow_person_uncertainty,
        methods=["POST"],
    ),
    Route("/update_aow_person_id", update_aow_person_id, methods=["POST"]),
    Route("/add_person_and_association", add_person_and_association, methods=["POST"]),
    Route("/update_aow_person_detail", update_aow_person_detail, methods=["POST"]),
    Route("/update_aow_person_role", update_aow_person_role, methods=["POST"]),
]
