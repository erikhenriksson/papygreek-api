from xml.dom.minidom import parseString
import unicodedata

import re

from starlette.authentication import requires
from starlette.routing import Route
from starlette.responses import Response
from starlette.exceptions import HTTPException

from ..config import db
from ..response import JSONResponse
from .comments import insert_comment, get_comment
from .tokens import get_tokens_by_text
from .text import change_text_status

from lxml import etree


async def insert_artificial(text_id, layer, data):
    if layer == "orig":
        cols = [
            "orig_form",
            "orig_lemma",
            "orig_postag",
            "orig_relation",
            "orig_head",
            "reg_form",
        ]
    elif layer == "reg":
        cols = [
            "reg_form",
            "reg_lemma",
            "reg_postag",
            "reg_relation",
            "reg_head",
            "orig_form",
        ]
    else:
        return {"ok": False, "result": "No layer"}
    result = await db.execute(
        f"""
        INSERT INTO token (text_id, {cols[0]}, {cols[1]}, {cols[2]}, {cols[3]}, {cols[4]}, {cols[5]},  insertion_id, artificial, sentence_n, n) 
        VALUES (%(text_id)s, %(form)s, %(lemma)s, %(postag)s, %(relation)s, %(head)s, %(form_other_layer)s, %(insertion_id)s, %(artificial)s, %(sentence_n)s, %(n)s)
        """,
        {
            "text_id": text_id,
            "form": data.get("form", None),
            "lemma": data.get("lemma", None),
            "postag": data.get("postag", None),
            "relation": data.get("relation", None),
            "head": data.get("head", None),
            "form_other_layer": data.get("form", None),
            "insertion_id": data.get("insertion_id", None),
            "artificial": data.get("artificial", None),
            "sentence_n": data.get("pg_sid", None),
            "n": data.get("id", None),
        },
    )

    return result


async def delete_artificial(token_id):
    deleted = await db.execute(
        """
        DELETE 
          FROM token 
         WHERE id = %s 
           AND artificial = 'elliptic'
    """,
        (token_id,),
    )

    return deleted


async def update_token_annotation(layer, data):
    if layer == "orig":
        cols = ["orig_lemma", "orig_postag", "orig_relation", "orig_head"]
    elif layer == "reg":
        cols = ["reg_lemma", "reg_postag", "reg_relation", "reg_head"]
    else:
        return {"ok": False, "result": "No layer"}
    update_artificial_form = (
        f"{layer}_form = %(artificial_form)s,"
        if (data.get("artificial") or "").strip()
        else ""
    )

    update = await db.execute(
        f"""
        UPDATE token 
           SET {update_artificial_form}
               {cols[0]} = %(lemma)s, 
               {cols[1]} = %(postag)s, 
               {cols[2]} = %(relation)s, 
               {cols[3]} = %(head)s, 
               insertion_id = %(insertion_id)s, 
               artificial = %(artificial)s
        WHERE id = %(token_id)s
    """,
        {
            "artificial_form": data.get("form", ""),
            "lemma": data.get("lemma", None),
            "postag": data.get("postag", None),
            "relation": data.get("relation", None),
            "head": data.get("head", None),
            "insertion_id": data.get("insertion_id", None),
            "artificial": data.get("artificial", None),
            "token_id": data.get("pg_id", None),
        },
    )

    return update


async def get_layer(request):
    text_id = request.path_params["doc"]
    layer = request.path_params["layer"]
    tokens = await db.fetch_all(
        """
        SELECT * 
          FROM token 
         WHERE text_id = %(id)s 
         ORDER BY sentence_n, n
        """,
        {"id": text_id},
    )
    tokens = tokens["result"]
    root = etree.Element(
        "treebank",
        attrib={
            "text_id": str(text_id),
            "layer": layer,
            "format": "aldt",
            "version": "1.5",
            "direction": "ltr",
        },
        nsmap={"saxon": "http://saxon.sf.net/"},
    )

    attr = root.attrib  # A hack for lang:grc
    attr["{http://www.w3.org/XML/1998/namespace}lang"] = "grc"
    s = []
    for i, token in enumerate(tokens):
        if i == 0 or token["sentence_n"] != tokens[i - 1]["sentence_n"]:
            s = etree.SubElement(
                root,
                "sentence",
                attrib={
                    "id": str(token["sentence_n"]),
                },
                nsmap=None,
            )
        word = etree.Element("word", attrib={}, nsmap=None)
        atts_to_add = [
            "insertion_id",
            "artificial",
            "id",
            "pg_id",
            f"{layer}_form",
            f"{layer}_postag",
            f"{layer}_lemma",
            f"{layer}_relation",
            f"{layer}_head",
        ]

        for key, val in token.items():
            if key in atts_to_add:
                if key in ["artificial", "insertion_id"] and not val:
                    continue

                val = str(val) if val is not None else ""

                if key == f"{layer}_form":
                    orig_val = val
                    val = val.replace("‹", "<").replace("›", ">")
                    val = val.replace("_[", "[]").replace("]_", "]")
                    val = val.replace("|_", "[]").replace("_|", "]")
                    val = val.replace("<_", "").replace("_>", "")
                    val = val.replace("<|", "").replace("|>", "")
                    val = val.replace("←:", "").replace("→:", "").replace("↕:", "")
                    char_filter = (
                        ",.·;;·[]〚〛<>(){}?" if layer == "orig" else ",.·;;·[]<>?"
                    )
                    val = "".join(
                        [
                            unicodedata.normalize("NFD", a)
                            for a in val
                            if a.isalpha() or a.isnumeric() or a in char_filter
                        ]
                    )
                    val = val.replace('()', '')
                    if not val:
                        val = orig_val

                if key == "id":
                    word.set("pg_id", str(token["id"]))

                word.set(key.split(f"{layer}_")[-1], val)
        """
        if (token["artificial"] or "").strip():
            reg_form_art = (token["reg_form"] or "").strip()
            orig_form_art = (token["orig_form"] or "").strip()

            if not (reg_form_art and orig_form_art):
                if reg_form_art:
                    word.set("form", reg_form_art)
                if orig_form_art:
                    word.set("form", orig_form_art)
        """

        word.set("line_n", str(token.get("line", "")))
        word.set("lang", str(token.get("lang", "")))
        word.set("hand", str(token.get("hand", "")))
        word.set("id", str(token.get("n", "")))

        s.append(word)

    xml = etree.tostring(root)

    return Response(xml, media_type="text/xml")


@requires("editor")
async def save_layer(request):
    user = request.user
    text_id = request.path_params["doc"]
    layer = request.path_params["layer"]
    body = await request.body()
    layer_dom = parseString(body.decode())

    root = layer_dom.getElementsByTagName("treebank")
    try:
        text_id = root[0].getAttribute("text_id")
        layer = root[0].getAttribute("layer")
    except:
        raise HTTPException(500)

    sentences = root[0].getElementsByTagName("sentence")
    arethusa_existing_tokens = []
    arethusa_new_artificials = []

    for sentence in sentences:
        for token in sentence.childNodes:
            if token.nodeType == 1:
                atts = token.attributes.items()
                atts.append(("pg_sid", sentence.getAttribute("id")))
                token_dict = dict((x, y) for x, y in atts)
                if not token_dict.get("pg_id", None):
                    arethusa_new_artificials.append(token_dict)
                else:
                    arethusa_existing_tokens.append(token_dict)

    old_tokens = await get_tokens_by_text(text_id)
    arethusa_artificials_with_id = set(
        [
            int(x["pg_id"])
            for x in arethusa_existing_tokens
            if x.get("artificial", "") == "elliptic"
        ]
    )
    db_artificials_with_id = set(
        [
            int(x["id"])
            for x in old_tokens["result"]
            if x.get("artificial", "") == "elliptic"
        ]
    )

    deleted_artificials = list(
        set(db_artificials_with_id).difference(arethusa_artificials_with_id)
    )

    for art_id in deleted_artificials:
        await delete_artificial(art_id)

    for token in arethusa_existing_tokens:
        await update_token_annotation(layer, token)

    for token in arethusa_new_artificials:
        await insert_artificial(text_id, layer, token)

    await insert_comment(text_id, user.id, 2, "1", layer)
    await change_text_status(text_id, 1, [layer], "0,2")

    return JSONResponse({"ok": True})


@requires("editor")
async def save_layer_comment(request):
    user = request.user
    text_id = request.path_params["doc"]
    layer = request.path_params["layer"]
    body = await request.json()

    comment_id = await insert_comment(text_id, user.id, 3, body["comment"], layer)

    if comment_id["ok"]:
        comment_formatted = await get_comment(comment_id["result"])
        if comment_formatted["ok"]:
            return JSONResponse(comment_formatted["result"])
        return 500


async def get_layer_comments(request):
    text_id = request.path_params["doc"]
    layer = request.path_params["layer"]
    comments = await db.fetch_all(
        """
        SELECT comment.id AS comment_id, 
               `text` AS comment, 
               DATE_FORMAT(created, '%%Y-%%m-%%dT%%TZ') AS created_at, 
               DATE_FORMAT(created, '%%Y-%%m-%%dT%%TZ') AS updated_at, 
               user.name AS user
          FROM comment
               INNER JOIN user
               ON comment.user_id = user.id
         WHERE text_id = %(id)s
           AND layer = %(layer)s
           AND type = 3
         ORDER BY created_at ASC
    """,
        {"id": text_id, "layer": layer},
    )

    return JSONResponse(comments["result"])


routes = [
    Route("/{doc}/{layer}", get_layer, methods=["GET"]),
    Route("/{doc}/{layer}", save_layer, methods=["POST"]),
    Route("/{doc}/{layer}/comments", get_layer_comments, methods=["GET"]),
    Route("/{doc}/{layer}/comments", save_layer_comment, methods=["POST"]),
]
