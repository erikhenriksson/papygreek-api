from starlette.routing import Route

from starlette.authentication import requires
from ..response import JSONResponse

from . import tokens, comments, text
from ..config import db
from ..utils import plain, grave_to_acute


async def update_annotation(data):
    # Validate data. The options below are the valid formats for linguistic
    # annotations.
    valid_keys = [
        "orig_lemma",
        "orig_lemma_plain",
        "orig_postag",
        "orig_relation",
        "orig_head",
        "reg_lemma",
        "reg_lemma_plain",
        "reg_postag",
        "reg_relation",
        "reg_head",
        "insertion_id",
        "artificial",
        "lemma_orig",
        "lemma_orig_plain",
        "postag_orig",
        "relation_orig",
        "head_orig",
        "lemma_reg",
        "lemma_reg_plain",
        "postag_reg",
        "relation_reg",
        "head_reg",
        "postag",
        "lemma",
        "lemma_plain",
        "relation",
        "head",
        "n",
    ]
    assert all(elem in valid_keys for elem in data["data"].keys())
    update_data = {}

    # Normalize
    for k, v in data["data"].items():
        if k.endswith(("orig", "reg")):
            ks = k.split("_")
            update_data[f"{ks[1]}_{ks[0]}"] = v
        elif not ("orig" in k or "reg" in k) and any(
            [x in k for x in ["postag", "lemma", "relation", "head"]]
        ):
            update_data["orig_" + k] = v
            update_data["reg_" + k] = v
        else:
            update_data[k] = v

    if "orig_lemma" in update_data:
        update_data["orig_lemma"] = grave_to_acute(
            update_data.get("orig_lemma", "") or ""
        )
        update_data["orig_lemma_plain"] = plain(update_data.get("orig_lemma", "") or "")
    if "reg_lemma" in update_data:
        update_data["reg_lemma"] = grave_to_acute(
            update_data.get("reg_lemma", "") or ""
        )
        update_data["reg_lemma_plain"] = plain(update_data.get("reg_lemma", "") or "")

    # Convert to SQL string
    update_string = ", ".join([f"{k}=%({k})s " for k, v in update_data.items()])

    # Update
    update_data["token_id"] = data["token_id"]
    await db.execute(
        f"""
        UPDATE token 
           SET {update_string} 
         WHERE id = %(token_id)s
        """,
        update_data,
    )


async def add_artificial(data, sentence_n, text_id):
    # Validate data
    valid_keys = [
        "orig_form",
        "orig_lemma",
        "orig_lemma_plain",
        "orig_postag",
        "orig_relation",
        "orig_head",
        "reg_form",
        "reg_lemma",
        "reg_lemma_plain",
        "reg_postag",
        "reg_relation",
        "reg_head",
        "insertion_id",
        "artificial",
        "n",
    ]
    data = data["data"]
    assert all(elem in valid_keys for elem in data.keys())
    data["orig_lemma"] = grave_to_acute(data.get("orig_lemma", "") or "")
    data["reg_lemma"] = grave_to_acute(data.get("reg_lemma", "") or "")
    data["orig_lemma_plain"] = plain(data.get("orig_lemma", "") or "")
    data["reg_lemma_plain"] = plain(data.get("reg_lemma", "") or "")

    # Add fields
    data["sentence_n"] = sentence_n
    data["text_id"] = text_id
    data["pending_deletion"] = 0

    # Convert to SQL string
    add_keys = ", ".join([x for x in data.keys()])
    add_values = ", ".join([f"%({k})s" for k, v in data.items()])

    # Add artificial
    await db.execute(
        f"""
        INSERT INTO token ({add_keys}) 
        VALUES ({add_values})
        """,
        data,
    )


@requires("editor")
async def edit_sentence_annotation(request):
    q = await request.json()

    for token in q["edit"]:
        await update_annotation(token)

    for token_id in q["delete"]:
        await db.execute(
            """
            DELETE FROM token 
             WHERE id = %s 
               AND (artificial = 'elliptic' 
                OR orig_form IN ('[0]', '[1]', '[2]', '[3]', '[4]', '[5]', '[6]', '[7]', '[8]', '[9]') 
                OR reg_form IN ('[0]', '[1]', '[2]', '[3]', '[4]', '[5]', '[6]', '[7]', '[8]', '[9]'))
            """,
            (token_id,),
        )

    for token in q["add"]:
        await add_artificial(token, q["sentence_n"], q["text_id"])

    # Add comment: text edited
    for layer in ["orig", "reg"]:
        await comments.insert_comment(q["text_id"], request.user.id, 2, "1", layer)  # type: ignore

    # Change status to 1 if previous status was 0 or 2
    await text.change_text_status(q["text_id"], 1, ["orig", "reg"], "0,2")

    # Return new sentence
    return JSONResponse(
        await tokens.get_tokens_by_sentence(q["text_id"], q["sentence_n"])
    )


routes = [
    Route("/edit", edit_sentence_annotation, methods=["PATCH", "POST"]),
]
