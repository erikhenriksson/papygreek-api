from starlette.routing import Route
from ..config import db
from ..response import JSONResponse
from starlette.authentication import requires
from ..utils import cols


async def get_persons(request):
    result = await db.fetch_all(
        """
        SELECT *, 
               GROUP_CONCAT(DISTINCT aow_person.role) AS roles 
          FROM person
               LEFT JOIN aow_person
               ON aow_person.person_id = person.id
         GROUP BY person.id
         ORDER BY person.name, person.id, role
        """
    )

    return JSONResponse(result)


async def get_persons_and_texts(request):
    result = await db.fetch_all(
        """
        SELECT *, 
               GROUP_CONCAT(DISTINCT aow_person.role) AS roles ,
               GROUP_CONCAT(CONCAT(aow_person.role, '|', text.name, '|', text.id, '|', COALESCE(aow_person.uncertain, 0 ))) AS texts
          FROM person
               LEFT JOIN aow_person
               ON aow_person.person_id = person.id
          LEFT JOIN `text` ON aow_person.text_id = `text`.id
         GROUP BY person.id
         ORDER BY person.name, person.id, role;
        """
    )

    return JSONResponse(result)


async def get_person(request):
    data = await db.fetch_all(
        """
        SELECT person.name,
               person.tm_id,
               person.gender,
               aow_person.role,
               aow_person.text_id,
               aow_person.aow_n,
               aow_person.uncertain,
               `text`.name as text_name
         FROM person
              LEFT JOIN aow_person 
              ON aow_person.person_id = person.id
              LEFT JOIN `text` 
              ON aow_person.text_id = `text`.id
        WHERE person.id = %(id)s
    """,
        request.path_params,
    )

    return JSONResponse(data)


@requires("editor")
async def update_person(request):
    q = await request.json()
    assert q["item"] in cols("person")
    result = await db.execute(
        f"""
        UPDATE person 
           SET {q["item"]} = %(val)s 
         WHERE id = %(id)s
    """,
        ({"id": request.path_params["id"], "val": q["value"]}),
    )

    return JSONResponse(result)


routes = [
    Route("/all", get_persons),
    Route("/expanded", get_persons_and_texts),
    Route("/{id:int}", get_person),
    Route("/{id:int}", update_person, methods=["PATCH", "POST"]),
]
