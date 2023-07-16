from starlette.routing import Route
from ..response import JSONResponse
from starlette.authentication import requires

from ..config import db


@requires("admin")
async def slow_query(request):
    response = await db.fetch_one(
        """
        SELECT benchmark(10000000, md5('when will it end?'));
    """
    )
    return JSONResponse(response)


routes = [
    Route("/slow_query", slow_query),
]
