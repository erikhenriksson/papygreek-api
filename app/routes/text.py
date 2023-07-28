from starlette.routing import Route
from starlette.authentication import requires
from starlette.responses import PlainTextResponse
from ..response import JSONResponse

import json

from . import tokens, comments, xml
from ..config import db
from ..textmanager import variations, closures
from papygreektokenizer import format_token_html


async def get_text_tokens(request):
    data = await tokens.get_tokens_by_text(request.path_params["id"])
    return JSONResponse(data)


async def get_text_tokens_html(request):
    data = await tokens.get_tokens_by_text(request.path_params["id"])
    print(data)
    for token in data["result"]:
        orig_elements = json.loads(token["orig_data"] or "{}")
        reg_elements = json.loads(token["reg_data"] or "{}")
        token["orig_html"] = format_token_html(
            token["orig_form_unformatted"] or "", orig_elements
        )
        token["reg_html"] = format_token_html(
            token["reg_form_unformatted"] or "", reg_elements
        )
    return JSONResponse(data)


async def change_text_status(text_id, status, layers, require_prev_status=None):
    """
    Text status numbering:
        0 = Not yet annotated
        1 = In progress
        2 = Rejected
        3 = Finalized
        6 = Submitted
        8 = Migrated
    """
    for layer in layers:
        assert layer in ["orig", "reg"]
        layer_key = f"{layer}_status"
        prev_status = (
            f"{layer_key} in ({require_prev_status}) AND" if require_prev_status else ""
        )
        await db.execute(
            f"""
            UPDATE `text` 
               SET {layer_key} = %s 
             WHERE {prev_status} id = %s
        """,
            (status, text_id),
        )


@requires("editor")
async def update_text_status(request):
    user = request.user
    q = await request.json()

    layer = q["layer"]
    text_id = q["text_id"]
    status = q["status"]
    await change_text_status(text_id, status, [layer])
    await comments.insert_comment(text_id, user.id, 2, status, layer)

    return JSONResponse({"ok": True})


async def get_text_workflow(request):
    text_id = request.path_params["id"]
    comments = await db.fetch_all(
        """
        SELECT user_id,
               user.name AS name,
               `text`,
               `type`,
               layer,
               DATE(created)
          FROM comment
               JOIN user
               ON user.id = comment.user_id
         WHERE text_id = %s
         ORDER BY created
    """,
        (text_id,),
    )

    status = await db.fetch_one(
        """
        SELECT orig_status,
               reg_status
          FROM `text`
         WHERE id = %s
    """,
        (text_id,),
    )

    header = await xml.get_xml_header(text_id)

    try:
        reg_comments = [x for x in comments["result"] if x["layer"] == "reg"]
        orig_comments = [x for x in comments["result"] if x["layer"] == "orig"]
        orig_status = status["result"]["orig_status"]
        reg_status = status["result"]["reg_status"]

        orig_header = {"approved": [], "annotated": [], "annotated (previously)": []}
        reg_header = {"approved": [], "annotated": [], "annotated (previously)": []}

        for h in header:
            if h["layer"] == "orig":
                orig_header[h["role"]].append(h)
            elif h["layer"] == "reg":
                reg_header[h["role"]].append(h)

        return JSONResponse(
            {
                "ok": True,
                "result": {
                    "reg": reg_comments,
                    "orig": orig_comments,
                    "orig_status": orig_status,
                    "reg_status": reg_status,
                    "orig_header": orig_header,
                    "reg_header": reg_header,
                },
            }
        )
    except:
        return JSONResponse({"ok": True, "result": "Error"})


async def get_text(request):
    data = await db.fetch_one(
        """
        SELECT `text`.id AS id, 
               series_name,
               series_type,
               `text`.name AS name, 
               xml_papygreek,
               xml_original,
               tm,
               hgv,
               date_not_after,
               date_not_before,
               place_name,
               DATE(tokenized) AS tokenized,
               DATE(checked) AS checked,
               orig_status,
               reg_status,
               `current`
          FROM `text`
         WHERE `text`.id = %(id)s
    """,
        request.path_params,
    )

    return JSONResponse(data)


async def get_text_xml(request):
    text = await db.fetch_one(
        """
        SELECT * 
          FROM `text` 
         WHERE id = %(id)s
        """,
        request.path_params,
    )
    xml_str = await xml.generate_treebank(text["result"])
    xml_str = xml_str.decode("utf-8")
    return JSONResponse({"ok": True, "result": xml_str})


async def get_text_name(text_id):
    result = await db.fetch_one(
        """
        SELECT name 
          FROM `text` 
         WHERE id = %(id)s
        """,
        (text_id,),
    )
    if result["ok"]:
        return result["result"]
    return "?"


async def request_tokenization(request):
    q = await request.json()
    text_id = request.path_params["id"]
    text_status = await db.fetch_one(
        """
        SELECT orig_status,
               reg_status
          FROM `text`
         WHERE id = %s
    """,
        (text_id,),
    )

    annotated = bool(
        text_status["result"]["orig_status"] or text_status["result"]["reg_status"]
    )
    best_matches = None
    if annotated:
        old_sentences = await tokens.get_text_sentences(text_id)
        new_sentences = tokens.xml_to_sentences(q["xml"])
        best_matches = await tokens.get_best_sentence_matches(
            old_sentences, new_sentences
        )
    return JSONResponse(
        {"ok": True, "result": {"annotated": annotated, "matches": best_matches}}
    )


async def confirm_tokenization(request):
    # User confirms a new tokenization

    q = await request.json()
    text_id = request.path_params["id"]
    imports = q["import"] or []
    import_map = []
    old_sentences = []
    new_sentences = tokens.xml_to_sentences(q["xml"])

    if imports:
        old_sentences = await tokens.get_text_sentences(text_id)

        best_matches = await tokens.get_best_sentence_matches(
            old_sentences, new_sentences
        )
        import_map = [
            x["old_sentence"] if int(imports[i]) else -1
            for i, x in enumerate(best_matches)
        ]
    result = await tokens.insert_tokens_and_import_annotation(
        text_id, old_sentences, new_sentences, import_map
    )
    if not result["ok"]:
        return JSONResponse(result)
    text_status = await db.fetch_one(
        """
        SELECT orig_status,
               reg_status
          FROM `text`
         WHERE id = %s
    """,
        (text_id,),
    )
    annotated = bool(
        text_status["result"]["orig_status"] or text_status["result"]["reg_status"]
    )

    if annotated:
        text = await db.fetch_one(
            """
            SELECT * 
              FROM `text` 
             WHERE id = %s
        """,
            (text_id,),
        )
        xml_str = await xml.generate_treebank(text["result"])
        xml_str = xml_str.decode("utf-8")
        backup = await db.execute(
            """
            INSERT INTO treebank_backup (text_id, treebank_XML) 
            VALUES (%s, %s)
        """,
            (text_id, xml_str),
        )
        if not backup["ok"]:
            return JSONResponse(backup)

    updated_xml = await db.execute(
        """
        UPDATE text
           SET xml_papygreek = %s, 
               tokenized = NOW()
         WHERE id = %s
        """,
        (
            q["xml"],
            text_id,
        ),
    )
    if not updated_xml["ok"]:
        return JSONResponse(updated_xml)

    updated_variations = await variations.update_text_variations(text_id)

    if not updated_variations["ok"]:
        return JSONResponse(updated_variations)

    updated_closures = await closures.update_text_closures(text_id)

    if not updated_closures["ok"]:
        return JSONResponse(updated_closures)

    return JSONResponse({"ok": True, "result": ""})


async def list_backups(request):
    # List all backups stored for a text
    result = await db.fetch_all(
        """
        SELECT * 
          FROM treebank_backup 
         WHERE text_id = %(id)s 
         ORDER BY created DESC
    """,
        (request.path_params),
    )
    return JSONResponse(result)


async def get_backup(request):
    # Get treebank backup for a text in plaintext
    backup = await db.fetch_one(
        """
        SELECT treebank_xml 
          FROM treebank_backup 
         WHERE text_id = %(text_id)s 
           AND id = %(backup_id)s
    """,
        (request.path_params),
    )
    return PlainTextResponse(backup["result"]["treebank_xml"])


routes = [
    Route("/{id:int}", get_text),
    Route("/{id:int}/tokens", get_text_tokens),
    Route("/{id:int}/tokens_html", get_text_tokens_html),
    Route("/{id:int}/workflow", get_text_workflow),
    Route("/{id:int}/update_status", update_text_status, methods=["PATCH", "POST"]),
    Route("/{id:int}/xml", get_text_xml),
    Route("/{id:int}/request_tokenization", request_tokenization, methods=["POST"]),
    Route("/{id:int}/confirm_tokenization", confirm_tokenization, methods=["POST"]),
    Route("/{id:int}/archive", list_backups),
    Route("/{text_id:int}/archive/{backup_id:int}", get_backup),
]
