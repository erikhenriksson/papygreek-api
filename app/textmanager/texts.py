import glob
import os
from itertools import zip_longest
from pprint import pprint
from epidoctokenizer import tokenize_file, tokenize_string
from tabulate import tabulate

from ..config import db, IDP_PATH
from ..routes import tokens


async def tokens_have_changed(text_id, new_tokens):
    old_sentences = await tokens.get_text_sentences(text_id)
    new_sentences = tokens.group_tokens_to_sentences(new_tokens)

    sames = await same_sentences(old_sentences, new_sentences)

    return not sames


async def same_sentences(old_sentences, new_sentences):
    old_sentences_without_artificials = []
    for s in old_sentences:
        old_sentences_without_artificials.append(
            [x for x in s if not tokens.is_artificial(x)]
        )
    for new_sentence, old_sentence in zip_longest(
        new_sentences, old_sentences_without_artificials, fillvalue=[]
    ):
        for new_t, old_t in zip_longest(new_sentence, old_sentence, fillvalue={}):
            orig_new = new_t.get(f"orig_form", "")
            orig_old = old_t.get(f"orig_form", "[none]")
            reg_new = new_t.get(f"reg_form", "")
            reg_old = old_t.get(f"reg_form", "[none]")
            if orig_new != orig_old or reg_new != reg_old:
                return 0

    return 1


async def check_tokenizations(db_text, name, path):
    def color(s, color=""):
        colors = {
            "": "\033[39m",
            "green": "\033[92m",
            "blue": "\033[94m",
            "yellow": "\033[33m",
            "red": "\033[31m",
        }
        return f"{colors[color]}{s}\033[0m"

    tokenizer = tokenize_string(db_text["xml_papygreek"])
    new_tokens = tokenizer["tokens"]()["tokens"]

    old_sentences = await tokens.get_text_sentences(db_text["id"])
    new_sentences = tokens.group_tokens_to_sentences(new_tokens)

    if not db_text.get("v1", "") and (db_text["orig_status"] or db_text["reg_status"]):
        same_sent = await same_sentences(old_sentences, new_sentences)
        if not same_sent:
            old_sentences_without_artificials = []
            for s in old_sentences:
                old_sentences_without_artificials.append(
                    [x for x in s if not tokens.is_artificial(x)]
                )

            tabu_tokens = []
            tabu_header = [
                "old_s",
                "old_n",
                "old_orig",
                "old_reg",
                "|",
                "new_s",
                "new_n",
                "new_orig",
                "new_reg",
            ]
            for new_sentence, old_sentence in zip_longest(
                new_sentences, old_sentences_without_artificials, fillvalue=[]
            ):
                for new_t, old_t in zip_longest(
                    new_sentence, old_sentence, fillvalue={}
                ):
                    orig_new = new_t.get(f"orig_form", "")
                    orig_old = old_t.get(f"orig_form", "[none]")
                    reg_new = new_t.get(f"reg_form", "")
                    reg_old = old_t.get(f"reg_form", "[none]")
                    c = ""
                    if orig_new != orig_old or reg_new != reg_old:
                        c = "red"

                    tabu_tokens.append(
                        [
                            color(old_t.get("sentence_n", ""), c),
                            color(old_t.get("n", ""), c),
                            color(old_t.get("orig_form", ""), c),
                            color(old_t.get("reg_form", ""), c),
                            color("|", c),
                            color(new_t.get("sentence_n", ""), c),
                            color(new_t.get("n", ""), c),
                            color(new_t.get("orig_form", ""), c),
                            color(new_t.get("reg_form", ""), c),
                        ]
                    )

            print(tabulate(tabu_tokens, tabu_header))
            print(name)
            print(db_text["id"])
            print(path)
            for new_sentence, old_sentence in zip_longest(
                new_sentences, old_sentences_without_artificials, fillvalue=[]
            ):
                print(len(new_sentence), len(old_sentence))
            exit()
    return {"ok": True, "result": ""}


async def check_tokenizer_for_annotated_texts():
    result = await db.fetch_all(
        """
        SELECT id, 
               name,
               series_type,
               xml_original, 
               xml_papygreek,
               v1
          FROM `text`
         WHERE NOT
               ((orig_status IS NULL 
               OR orig_status in (0)) 
               AND (reg_status is null 
               OR reg_status in (0)))
        """
    )

    db_texts = result["result"]

    for db_text in db_texts:
        if db_text["v1"]:
            continue

        tokenizer = tokenize_string(db_text["xml_papygreek"])
        xml_papygreek_tokens = tokenizer["tokens"]()["tokens"]
        changed_tokens = await tokens_have_changed(db_text["id"], xml_papygreek_tokens)
        if changed_tokens:
            return {
                "ok": False,
                "result": f"{db_text['name']} [{db_text['id']}]: tokens have changed",
            }

    return {"ok": True, "result": "done"}


async def run_one(path, series_type, flags):
    # Init tokenizer
    tokenizer = tokenize_file(path, f"{IDP_PATH}/HGV_meta_EpiDoc")

    # Get text meta
    meta = tokenizer["meta"]

    # See if text exists in database
    result = await db.fetch_one(
        """
        SELECT id, 
               checked,
               xml_original, 
               xml_papygreek,
               reg_status, 
               orig_status,
               v1
          FROM `text`
         WHERE name = %s
           AND series_name = %s
        """,
        (meta["name"], meta["series_name"]),
    )

    db_text = result["result"]

    # check_tokenizations flag: check and return
    if db_text and "check_tokenizations" in flags:
        return await check_tokenizations(db_text, meta["name"], path)

    if db_text and meta["last_change"] < db_text["checked"] and not "force" in flags:
        return {"ok": True, "result": f"{meta['name']}: up-to-date"}

    # Text has potentially changed, or forced to continue
    new_tokens = tokenizer["tokens"]()["tokens"]

    # No existing text or new tokens, do nothing
    if not (db_text or new_tokens):
        return {"ok": True, "result": f"{meta['name']}: nothing to add"}

    xml = tokenizer["edition_xml"]
    hgv_meta = tokenizer["hgv_meta"]()

    # New text and tokens
    if not db_text and new_tokens:
        result = await db.execute(
            """
            INSERT INTO `text`
                    (`series_name`,`series_type`,`name`, `language`, `xml_papygreek`,`xml_original`,
                    `tm`,`hgv`,`date_not_before`,`date_not_after`,`place_name`)
            VALUES (%s,%s,%s, %s,%s,%s,%s,%s,%s,%s,%s);
            """,
            (
                meta["series_name"],
                series_type,
                meta["name"],
                meta["language"],
                xml,
                xml,
                " ".join(meta["tm"]),
                " ".join(meta["hgv"]),
                hgv_meta["dnb"],
                hgv_meta["dna"],
                hgv_meta["place"],
            ),
        )
        if not result["ok"]:
            return result

        text_id = result["result"]
        result = await tokens.insert_tokens(new_tokens, text_id)
        if not result["ok"]:
            result["text_id"] = text_id
            return result
        return {"ok": True, "result": f"{meta['name']} [{text_id}]: added text"}

    # Old text exists
    text_id = db_text["id"]

    # Update meta
    result = await db.execute(
        """
        UPDATE `text`
           SET language = %s, 
               tm = %s, 
               hgv = %s, 
               date_not_before = %s, 
               date_not_after = %s, 
               place_name = %s, 
               checked = NOW()
         WHERE id = %s
        """,
        (
            meta["language"],
            " ".join(meta["tm"]),
            " ".join(meta["hgv"]),
            hgv_meta["dnb"],
            hgv_meta["dna"],
            hgv_meta["place"],
            text_id,
        ),
    )
    if not result["ok"]:
        result["text_id"] = text_id
        return result

    if xml == db_text["xml_original"] and not "retokenize" in flags:
        return {
            "ok": True,
            "result": f"{meta['name']} [{text_id}]: XML unchanged, updated meta",
        }

    # Updating a non-annotated text
    if not (db_text["orig_status"] or db_text["reg_status"]):
        if not new_tokens:
            result = await db.execute(
                """
                DELETE 
                  FROM `text`
                 WHERE id = %s
                """,
                (text_id,),
            )
            if not result["ok"]:
                result["text_id"] = text_id
                return result
            return {
                "ok": True,
                "result": f"{meta['name']} [{text_id}]: no tokens, deleted text",
            }

        result = await db.execute(
            """
            UPDATE `text`
               SET xml_papygreek = %s, 
                   xml_original = %s, 
                   xml_next = NULL,
                   tokenized = NOW(), 
                   checked = NOW(),
                   `current` = 1
             WHERE id = %s
            """,
            (
                xml,
                xml,
                text_id,
            ),
        )
        if not result["ok"]:
            result["text_id"] = text_id
            return result
        changed_tokens = await tokens_have_changed(text_id, new_tokens)
        if changed_tokens:
            result = await db.execute(
                """
                DELETE 
                FROM token
                WHERE text_id = %s
            """,
                (text_id,),
            )
            if not result["ok"]:
                result["text_id"] = text_id
                return result

            result = await tokens.insert_tokens(new_tokens, text_id)

            if not result["ok"]:
                result["text_id"] = text_id
                return result
            return {
                "ok": True,
                "result": f"{meta['name']} [{text_id}]: updated tokens and meta",
            }

        return {
            "ok": True,
            "result": f"{meta['name']} [{text_id}]: updated text meta, tokens unchanged",
        }

    # Annotated text: try to merge annotation

    # First, however, check if we are just retokenizing. In that case,
    # if the XML has not changed (as below), we just want to retokenize
    # the current XML (that is, xml_papygreek), hoping that it will not
    # break the annotation.
    if xml == db_text["xml_original"] and "retokenize" in flags:
        tokenizer = tokenize_string(db_text["xml_papygreek"])
        xml_papygreek_tokens = tokenizer["tokens"]()["tokens"]
        changed_tokens = await tokens_have_changed(text_id, xml_papygreek_tokens)
        if changed_tokens:
            # Tokenizer has changed. We must make text noncurrent and ask user to merge manually.
            result = await db.execute(
                """
                UPDATE `text`
                SET current = 0, 
                    xml_next = %s,
                    checked = NOW()
                WHERE id = %s
                """,
                (db_text["xml_papygreek"], text_id),
            )
            if not result["ok"]:
                return result
            return {
                "ok": True,
                "result": f"{meta['name']} [{text_id}]: tokenizer changed. Flagged noncurrent.",
            }
        return {
            "ok": True,
            "result": f"{meta['name']} [{text_id}]: checked tokenizer, nothing changed.",
        }

    # New XML has arrived

    new_sentences = tokens.group_tokens_to_sentences(new_tokens)
    old_sentences = await tokens.get_text_sentences(text_id)
    best_matches = await tokens.get_best_sentence_matches(
        old_sentences, new_sentences, "full-match"
    )
    import_map = [x["old_sentence"] if x["match"] else -1 for x in best_matches]
    mergable = not any(x == -1 for x in import_map)

    if mergable:
        result = await tokens.insert_tokens_and_import_annotation(
            text_id, old_sentences, new_sentences, import_map
        )
        if not result["ok"]:
            return result
        result = await db.execute(
            """
            UPDATE `text`
               SET xml_papygreek = %s, 
                   xml_original = %s, 
                   xml_next = NULL,
                   tokenized = NOW(), 
                   checked = NOW(),
                   `current` = 1
             WHERE id = %s
            """,
            (
                xml,
                xml,
                text_id,
            ),
        )
        if not result["ok"]:
            return result
        return {
            "ok": True,
            "result": f"{meta['name']} [{text_id}]: imported annotations",
        }

    # Finally: flag text noncurrent (could not merge annotation)
    result = await db.execute(
        """
        UPDATE `text`
           SET current = 0, 
               xml_next = %s,
               checked = NOW()
         WHERE id = %s
        """,
        (xml, text_id),
    )
    if not result["ok"]:
        return result
    return {"ok": True, "result": f"{meta['name']} [{text_id}]: flagged noncurrent"}


async def cli(flags):
    """
    Flags:
        file
        verbose
        check_tokenization
        force
        retokenize
    """
    if "file" in flags:
        result = await run_one(flags[-1], "documentary", flags)
        print(result)
        exit()

    if "check_tokenizer_for_annotated_texts" in flags:
        result = await check_tokenizer_for_annotated_texts()
        print(result)
        exit()

    paths = {
        "documentary": f"{IDP_PATH}/DDB_EpiDoc_XML",
        "literary": f"{IDP_PATH}/DCLP",
    }
    for series_type, path in paths.items():
        total = len(glob.glob(f"{path}/**/*.xml", recursive=True))
        print(f"{series_type}: {total} documents")
        c = 0
        for root, dirs, files in os.walk(path):
            dirs.sort()
            for name in sorted(files, reverse=True):
                if name.endswith("xml"):
                    c += 1
                    if "verbose" in flags:
                        print(f"(verbose) Now tokenizing {os.path.join(root, name)}")
                    result = await run_one(os.path.join(root, name), series_type, flags)
                    if "verbose" in flags:
                        print(result)
                    if not result["ok"]:
                        print(f"(verbose) Problem: {result['result']}")
                        print(os.path.join(root, name))
                        if not "check_tokenizations" in flags:
                            exit()
                    if c % 100 == 0:
                        print(f"{(c/total):.2f}")
