from itertools import groupby
from itertools import zip_longest
from difflib import SequenceMatcher
from epidoctokenizer import tokenize_string

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
               artificial,
               insertion_id,
               orig_form,
               orig_plain,
               orig_flag,
               orig_app_type,
               orig_num,
               orig_num_rend,
               orig_lang,
               orig_info,
               orig_postag,
               orig_lemma,
               orig_relation,
               orig_head,
               reg_form,
               reg_plain,
               reg_flag,
               reg_app_type,
               reg_num,
               reg_num_rend,
               reg_lang,
               reg_info,
               reg_postag,
               reg_lemma,
               reg_relation,
               reg_head,
               pending_deletion)
        VALUES
               (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0);
        """,
        (
            text_id,
            token["n"],
            token["sentence_n"],
            token["line"],
            token["line_rend"],
            token["hand"],
            token["textpart"],
            token["aow_n"],
            token["artificial"],
            token["insertion_id"],
            token["orig_form"],
            token["orig_plain"],
            token["orig_flag"],
            token["orig_app_type"],
            token["orig_num"],
            token["orig_num_rend"],
            token["orig_lang"],
            token["orig_info"],
            token["orig_postag"],
            token["orig_lemma"],
            token["orig_relation"],
            token["orig_head"],
            token["reg_form"],
            token["reg_plain"],
            token["reg_flag"],
            token["reg_app_type"],
            token["reg_num"],
            token["reg_num_rend"],
            token["reg_lang"],
            token["reg_info"],
            token["reg_postag"],
            token["reg_lemma"],
            token["reg_relation"],
            token["reg_head"],
        ),
    )


async def insert_token_rdg(var, token_id):
    return await db.execute(
        """
        INSERT INTO token_rdg 
               (token_id,
               form,
               plain,
               flag,
               app_type,
               num,
               num_rend,
               lang,
               info)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            token_id,
            var["form"],
            var["plain"],
            var["flag"],
            var["app_type"],
            var["num"],
            var["num_rend"],
            var["lang"],
            var["info"],
        ),
    )


async def insert_tokens(new_tokens, text_id):
    for token in new_tokens:
        result = await insert_token(token, text_id)
        if not result["ok"]:
            return result
        token_id = result["result"]
        if token["vars"]:
            for var in token["vars"]:
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


def xml_to_sentences(xml):
    tokenizer = tokenize_string(xml)
    new_tokens = tokenizer["tokens"]()["tokens"]
    return group_tokens_to_sentences(new_tokens)


def is_artificial(x):
    return (
        (x.get("artificial", "") or "").strip()
        or x.get("orig_form", "") == "[0]"
        or x.get("reg_form") == "[0]"
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
