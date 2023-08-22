import regex as re
import unicodedata
from ..config import db

just_greek = lambda x: re.sub(r"\p{^Greek}", "", (x or ""))
plain = lambda s: "".join([unicodedata.normalize("NFD", a)[0].lower() for a in s])


async def lemmatize(form, postag):
    form = just_greek(form)

    result = await db.fetch_one(
        """
        SELECT lemma, lemma_plain
          FROM morpheus
         WHERE form = %(form)s
           AND postag = %(postag)s
        """,
        ({"form": form, "postag": postag}),
    )

    if result["ok"] and result["result"]:
        return {
            "lemma": result["result"]["lemma"],
            "lemma_plain": result["result"]["lemma_plain"],
        }

    form_plain = plain(form)

    result_plain = await db.fetch_one(
        """
        SELECT lemma, lemma_plain
            FROM morpheus
            WHERE form_plain = %(form_plain)s
            AND postag = %(postag)s
        """,
        ({"form_plain": form_plain, "postag": postag}),
    )

    if result_plain["ok"] and result_plain["result"]:
        return {
            "lemma": result_plain["result"]["lemma"],
            "lemma_plain": result_plain["result"]["lemma_plain"],
        }

    return {"lemma": None, "lemma_plain": None}
