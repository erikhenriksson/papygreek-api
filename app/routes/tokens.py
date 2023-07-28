from itertools import groupby
import json
from itertools import zip_longest
from difflib import SequenceMatcher
from papygreektokenizer import tokenize_string

from ..config import db


async def insert_token(token, text_id):
    return await db.execute(
        """
        INSERT INTO token 
               (text_id,
               n,
               sentence_n,
               line,
               line_rend,
               hand,
               textpart,
               aow_n,
               orig_form,
               orig_form_unformatted,
               orig_plain,
               orig_plain_transcript,
               orig_num,
               orig_num_rend,
               orig_lang,
               orig_variation_path,
               orig_lemma,
               orig_lemma_plain,
               orig_postag,
               orig_relation,
               orig_head,
               orig_data,
               reg_form,
               reg_form_unformatted,
               reg_plain,
               reg_plain_transcript,
               reg_num,
               reg_num_rend,
               reg_lang,
               reg_variation_path,
               reg_lemma,
               reg_lemma_plain,
               reg_postag,
               reg_relation,
               reg_head,
               reg_data,
               artificial,
               insertion_id,
               pending_deletion)
        VALUES
               (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            text_id,
            token["n"],
            token["sentence_n"],
            token.get("line", None),
            token.get("line_rend", None),
            token.get("hand", None),
            token.get("textpart", None),
            token.get("aow_n", None),
            token.get("orig_form", None),
            token.get("orig_form_unformatted", None),
            token.get("orig_plain", None),
            token.get("orig_plain_transcript", None),
            token.get("orig_num", None),
            token.get("orig_num_rend", None),
            token.get("orig_lang", None),
            token.get("orig_variation_path", None),
            token.get("orig_lemma", None),
            token.get("orig_lemma_plain", None),
            token.get("orig_postag", None),
            token.get("orig_relation", None),
            token.get("orig_head", None),
            json.dumps(token.get("orig_data", "")),
            token.get("reg_form", None),
            token.get("reg_form_unformatted", None),
            token.get("reg_plain", None),
            token.get("reg_plain_transcript", None),
            token.get("reg_num", None),
            token.get("reg_num_rend", None),
            token.get("reg_lang", None),
            token.get("reg_variation_path", None),
            token.get("reg_lemma", None),
            token.get("reg_lemma_plain", None),
            token.get("reg_postag", None),
            token.get("reg_relation", None),
            token.get("reg_head", None),
            json.dumps(token.get("reg_data", "")),
            token.get("artificial", None),
            token.get("insertion_id", None),
            0,
        ),
    )


async def insert_token_rdg(var, token_id):
    return await db.execute(
        """
        INSERT INTO token_rdg
               (token_id,
               form,
               form_unformatted,
               plain,
               plain_transcript,
               num,
               num_rend,
               lang,
               variation_path,
               data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            token_id,
            var.get("var_form", None),
            var.get("var_form_unformatted", None),
            var.get("var_plain", None),
            var.get("var_plain_transcript", None),
            var.get("var_num", None),
            var.get("var_num_rend", None),
            var.get("var_lang", None),
            var.get("var_variation_path", None),
            json.dumps(var.get("var_data", "")),
        ),
    )


async def insert_tokens(new_tokens, text_id):
    for token in new_tokens:
        result = await insert_token(token, text_id)
        if not result["ok"]:
            return result
        token_id = result["result"]
        if token["var"]:
            for var in token["var"]:
                var["var_data"] = json.dumps(var["var_data"])
                result = await insert_token_rdg(var, token_id)
                if not result["ok"]:
                    return result

    return {"ok": True, "result": "Inserted tokens"}


async def get_tokens_by_text(text_id):
    result = await db.fetch_all(
        """
        SELECT *
          FROM token
         WHERE text_id = %s
         ORDER BY sentence_n, n
        """,
        (text_id,),
    )

    return result


async def get_old_tokens_by_text(text_id):
    result = await db.fetch_all(
        """
        SELECT *
          FROM token_old
         WHERE text_id = %s
         ORDER BY sentence_n, n
        """,
        (text_id,),
    )

    return result


async def get_tokens_by_sentence(text_id, sentence_n):
    result = await db.fetch_all(
        """
        SELECT *
          FROM token
         WHERE text_id = %s
           AND sentence_n = %s
         ORDER BY sentence_n, n
        """,
        (text_id, sentence_n),
    )

    return result


async def activate_pending_deletion(text_id):
    result = await db.execute(
        """
        UPDATE token
           SET pending_deletion = 1
         WHERE text_id = %s
        """,
        (text_id,),
    )

    return result


async def rollback_pending_deletion(text_id):
    result = await db.execute(
        """
        UPDATE token
           SET pending_deletion = 0
         WHERE text_id = %s
        """,
        (text_id,),
    )

    return result


async def delete_not_pending_deletion(text_id):
    result = await db.execute(
        """
        DELETE 
          FROM token
         WHERE pending_deletion = 0
           AND text_id = %s
        """,
        (text_id,),
    )

    return result


async def delete_pending_deletion(text_id):
    result = await db.execute(
        """
        DELETE 
          FROM token
         WHERE pending_deletion=1
           AND text_id = %s
        """,
        (text_id,),
    )

    return result


def group_tokens_to_sentences(tokens):
    return [list(value) for _, value in groupby(tokens, lambda x: x["sentence_n"])]


async def get_text_sentences(text_id):
    result = await get_tokens_by_text(text_id)
    old_tokens = result["result"]
    return group_tokens_to_sentences(old_tokens)


async def get_old_text_sentences(text_id):
    result = await get_old_tokens_by_text(text_id)
    old_tokens = result["result"]
    return group_tokens_to_sentences(old_tokens)


def xml_to_sentences(xml):
    # Convert XML to sentences. Used by text.py routes
    tokenizer = tokenize_string(xml)
    new_tokens = tokenizer["tokens"]()["tokens"]
    return group_tokens_to_sentences(new_tokens)


def is_artificial(x):
    return (
        (x.get("artificial", "") or "").strip()
        or x.get("orig_form", "")
        in ["[0]", "[1]", "[2]", "[3]", "[4]", "[5]", "[6]", "[7]", "[8]", "[9]"]
        or x.get("reg_form")
        == ["[0]", "[1]", "[2]", "[3]", "[4]", "[5]", "[6]", "[7]", "[8]", "[9]"]
    )


async def get_best_sentence_matches(old_sentences, new_sentences, comparison="char"):
    # Init match list
    new_old_matches = []

    # Strip artificials from old sentences
    old_sentences_without_artificials = []
    for s in old_sentences:
        old_sentences_without_artificials.append([x for x in s if not is_artificial(x)])

    # Iterate new sentences and try to match with old sentences
    for new_s in new_sentences:
        new_old_matches.append([])
        for old_i, old_s in enumerate(old_sentences_without_artificials):
            errors = []
            score = 0
            for new_t, old_t in zip_longest(new_s, old_s, fillvalue={}):
                orig_new = new_t.get(f"orig_form", "")
                orig_old = old_t.get(f"orig_form", "[none]")
                orig_ratio = (
                    SequenceMatcher(None, orig_new, orig_old).ratio()
                    if comparison == "char"
                    else +(orig_new == orig_old)
                )
                reg_new = new_t.get(f"reg_form", "")
                reg_old = old_t.get(f"reg_form", "[none]")
                reg_ratio = (
                    SequenceMatcher(None, reg_new, reg_old).ratio()
                    if comparison == "char"
                    else +(reg_new == reg_old)
                )
                avg_ratio = (orig_ratio + reg_ratio) / 2
                score += avg_ratio

                if avg_ratio < 1:
                    errors.append(
                        {"orig": (orig_new, orig_old), "reg": (reg_new, reg_old)}
                    )

            score_weighted = score / len(new_s)
            new_old_matches[-1].append(
                {
                    "old_sentence": old_i,
                    "diffs": errors,
                    "score": score_weighted,
                    "will_import": +(score_weighted >= 0.9),
                    "match": +(score_weighted == 1),
                }
            )

    # Get best matches for new sentences
    best_matches = []
    for data in new_old_matches:
        sorted_diffs = sorted(data, key=lambda d: d["score"], reverse=True)
        best_match = (
            sorted_diffs[0]
            if sorted_diffs
            else {
                "old_sentence": -1,
                "diffs": [],
                "score": 0,
                "will_import": 0,
                "match": 0,
            }
        )
        best_matches.append(best_match)

    return best_matches


async def insert_tokens_and_import_annotation(
    text_id, old_sentences, new_sentences, import_map
):
    pending_activated = await activate_pending_deletion(text_id)
    if not pending_activated["ok"]:
        return {"ok": False, "result": "Could not activate pending deletion."}

    for new_si, new_s in enumerate(new_sentences):
        try:
            import_i = import_map[new_si]
            will_import = import_i != -1
        except:
            will_import = False
            import_i = 0

        old_s = (
            [x for x in old_sentences[import_i] if not is_artificial(x)]
            if will_import
            else []
        )

        for new_ti, new_t in enumerate(new_s):
            if will_import:
                new_t["orig_lemma"] = old_s[new_ti]["reg_lemma"]
                new_t["orig_postag"] = old_s[new_ti]["reg_postag"]
                new_t["orig_relation"] = old_s[new_ti]["reg_relation"]
                new_t["orig_head"] = old_s[new_ti]["reg_head"]
                new_t["reg_lemma"] = old_s[new_ti]["reg_lemma"]
                new_t["reg_postag"] = old_s[new_ti]["reg_postag"]
                new_t["reg_relation"] = old_s[new_ti]["reg_relation"]
                new_t["reg_head"] = old_s[new_ti]["reg_head"]

            res = await insert_token(new_t, text_id)
            if not res["ok"]:
                await delete_not_pending_deletion(text_id)
                await rollback_pending_deletion(text_id)
                return {"ok": False, "result": res["result"]}

        if will_import:
            old_artificials = [x for x in old_sentences[import_i] if is_artificial(x)]

            for a in old_artificials:
                a["sentence_n"] = new_si + 1  # Get sentence_n from current sentence
                res = await insert_token(a, text_id)

                if not res["ok"]:
                    await delete_not_pending_deletion(text_id)
                    await rollback_pending_deletion(text_id)
                    return {"ok": False, "result": "Could not insert artificial."}

    return await delete_pending_deletion(text_id)
