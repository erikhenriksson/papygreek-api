from starlette.routing import Route
from ..response import JSONResponse
from ..config import db


async def release_figures(request):
    texts = await db.fetch_one(
        """
        SELECT count(id) AS count 
          FROM `text` 
         WHERE orig_status = 3 
           AND reg_status=3
        """
    )
    tokens = await db.fetch_one(
        """
        SELECT count(token.id) AS count 
          FROM token 
               LEFT JOIN `text` 
               ON token.text_id = text.id 
         WHERE orig_status = 3 
           AND reg_status = 3
        """
    )
    sentences = await db.fetch_one(
        """
        SELECT count(DISTINCT sentence_n, text_id) AS count 
          FROM token 
               JOIN `text` 
                 ON token.text_id = text.id 
         WHERE orig_status = 3 
           AND reg_status = 3
        """
    )

    return JSONResponse(
        {
            "texts": texts["result"]["count"],
            "tokens": tokens["result"]["count"],
            "sentences": sentences["result"]["count"],
        }
    )


async def word_frequencies(request):
    words = await db.fetch_all(
        """
        SELECT form_orig_plain 
          FROM token
        """
    )
    common_words = {}
    for word in words["result"]:
        word_form = word["form_orig_plain"]
        if word_form not in common_words:
            common_words[word_form] = 1
            continue
        common_words[word_form] += 1
    sorted_words = dict(
        sorted(common_words.items(), key=lambda item: item[1], reverse=True)
    )
    first_hundred = dict(list(sorted_words.items())[:100])

    return JSONResponse({"words": first_hundred})


routes = [
    Route("/release_figures", release_figures),
    Route("/word_frequencies", word_frequencies),
]
