from io import BytesIO
import zipfile
import re

from starlette.routing import Route
from starlette.responses import Response
from starlette.authentication import requires

from ..config import db
from ..utils import text_types

from lxml import etree


async def get_aow_data(text_id, aow_n):
    aow_text_types = await db.fetch_all(
        """      
        SELECT text_type, 
               id, 
               hypercategory, 
               category, 
               subcategory, 
               `status`
          FROM aow_text_type
         WHERE text_id = %(text_id)s
           AND aow_n = %(aow_n)s
         ORDER BY id
        """,
        {"text_id": text_id, "aow_n": aow_n},
    )

    aow_people = await db.fetch_all(
        """     
        SELECT aow_person.id AS id, 
               person_id, 
               role, 
               handwriting, 
               honorific, 
               ethnic, 
               occupation, 
               domicile, 
               age, 
               education, 
               name, 
               tm_id, 
               uncertain, 
               gender
          FROM aow_person
               LEFT JOIN person
               ON aow_person.person_id = person.id
         WHERE text_id = %(text_id)s
           AND aow_n = %(aow_n)s
         ORDER BY id
        """,
        {"text_id": text_id, "aow_n": aow_n},
    )

    return {"text_types": aow_text_types["result"], "people": aow_people["result"]}


async def get_aows(tokens, text_id):
    h = ""
    h_n = 1
    aows = []

    for token in tokens:
        if "hand" in token and token["hand"] and token["hand"] != "None":
            if token["hand"] != h:
                aow_data = await get_aow_data(text_id, h_n)  # type: ignore
                aows.append(
                    {
                        "name": token["hand"],
                        "n": h_n,
                        "text_types": aow_data["text_types"],
                        "people": aow_data["people"],
                    }
                )
                h_n += 1
            h = token["hand"]

    return aows


async def get_xml_header(text_id):
    comments = await db.fetch_all(
        """
        SELECT comment.type AS `type`, 
               `text`, 
               created AS `date`, 
               user.name AS user, 
               comment.user_id AS user_id, 
               comment.id AS id, 
               layer, 
               user.email AS user_email
          FROM comment
               INNER JOIN user
               ON comment.user_id = user.id
         WHERE text_id = %(id)s
         ORDER BY `date` DESC
        """,
        {"id": text_id},
    )

    header_data = []
    have_approved = {"reg": 0, "orig": 0}
    annotators = []

    roles = {
        "3": "approved",
        "7": "annotated (previously)",
        "5": "annotated",
        "6": "annotated",
    }

    for comment in comments["result"]:
        if comment["type"] == 2:
            if comment["text"] not in roles.keys():
                continue
            if comment["text"] == "3":
                if have_approved[comment["layer"]]:
                    continue
                have_approved[comment["layer"]] = 1

            elif comment["text"] in ["5", "6"]:
                if (comment["layer"], comment["user_id"]) in annotators:
                    continue
                annotators.append((comment["layer"], comment["user_id"]))

            elif comment["text"] == "7":
                if (comment["layer"], comment["user_id"]) in annotators:
                    continue

            header_data.append(
                {
                    "who": comment["user"],
                    "address": comment["user_email"],
                    "when": comment["date"].strftime("%Y-%m-%d"),
                    "role": roles[comment["text"]],
                    "layer": comment["layer"],
                }
            )

    return header_data


async def generate_treebank(text):
    tokens = await db.fetch_all(
        """
        SELECT * 
          FROM token 
         WHERE text_id = %(id)s 
         ORDER BY sentence_n, n
        """,
        {"id": text["id"]},
    )
    tokens = tokens["result"]
    root = etree.Element(
        "treebank",
        attrib={
            "text_id": str(text["id"]),
            "format": "aldt",
            "version": "1.5",
            "direction": "ltr",
        },
        nsmap={"saxon": "http://saxon.sf.net/"},
    )

    attr = root.attrib  # A hack for lang:grc
    attr["{http://www.w3.org/XML/1998/namespace}lang"] = "grc"

    header_data = await get_xml_header(text["id"])
    for hd in header_data:
        attributes = {
            "name": hd["who"],
            "address": hd["address"],
            "role": hd["role"],
            "date": hd["when"],
            "layer": hd["layer"],
        }

        etree.SubElement(root, "annotator", attrib=attributes, nsmap=None)

    # Metadata headers
    etree.SubElement(
        root,
        "document_meta",
        attrib={
            "name": str(text["name"] or ""),
            "series_name": str(text["series_name"] or ""),
            "series_type": str(text["series_type"] or ""),
            "tm_id": str(text["tm"] or ""),
            "hgv_id": str(text["hgv"] or ""),
            "date_not_before": str(text["date_not_before"] or ""),
            "date_not_after": str(text["date_not_after"] or ""),
            "place_name": str(text["place_name"] or ""),
        },
        nsmap=None,
    )

    aows = await get_aows(tokens, text["id"])
    for aow in aows:
        hand = etree.SubElement(
            root,
            "hand_meta",
            attrib={
                "name": aow["name"],
                "id": str(aow["n"]),
            },
            nsmap=None,
        )

        tt_strings_ghent = text_types()

        for tt in aow["text_types"]:
            text_type = etree.Element("text_type", attrib={}, nsmap=None)

            hypercat = (
                str(tt_strings_ghent[tt["hypercategory"]][0])
                if tt_strings_ghent[tt["hypercategory"]][0] not in [None, "---"]
                else ""
            )
            cat = (
                str(tt_strings_ghent[tt["hypercategory"]][1][tt["category"]][0])
                if tt_strings_ghent[tt["hypercategory"]][1][tt["category"]][0]
                not in [None, "---"]
                else ""
            )
            subcat = (
                str(
                    tt_strings_ghent[tt["hypercategory"]][1][tt["category"]][1][
                        tt["subcategory"]
                    ]
                )
                if tt_strings_ghent[tt["hypercategory"]][1][tt["category"]][1][
                    tt["subcategory"]
                ]
                not in [None, "---"]
                else ""
            )
            text_type.set("hypercategory", hypercat)
            text_type.set("category", cat)
            text_type.set("subcategory", subcat)

            hand.append(text_type)

        for aow_person in aow["people"]:
            person = etree.Element("person", attrib={}, nsmap=None)
            if aow_person["handwriting"]:
                # Remove odd double spaces
                aow_person["handwriting"] = re.sub(" +", " ", aow_person["handwriting"])

            if aow_person["gender"] == 1:
                aow_person["gender"] = "male"
            if aow_person["gender"] == 2:
                aow_person["gender"] = "female"

            person.set("pg_id", str(aow_person["person_id"] or ""))
            person.set("tm_id", str(aow_person["tm_id"] or ""))
            person.set("role", str(aow_person["role"] or ""))
            person.set("handwriting", aow_person["handwriting"] or "")
            person.set("honorific_epithet", aow_person["honorific"] or "")
            person.set("ethnic_label", aow_person["ethnic"] or "")
            person.set("occupation", aow_person["occupation"] or "")
            person.set("domicile", aow_person["domicile"] or "")
            person.set("age", aow_person["age"] or "")
            person.set("education", aow_person["education"] or "")
            person.set("name", aow_person["name"] or "")
            person.set("gender", aow_person["gender"] or "")
            person.set("uncertain", str(aow_person["uncertain"] or ""))

            hand.append(person)
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

        sql_to_att_map = {
            "insertion_id": "insertion_id",
            "artificial": "artificial",
            "id": "id",
            "pg_id": "pg_id",
            "orig_form": "orig_form",
            "orig_postag": "postag_orig",
            "orig_lemma": "lemma_orig",
            "orig_relation": "relation_orig",
            "orig_head": "head_orig",
            "reg_form": "form_reg",
            "reg_postag": "postag_reg",
            "reg_lemma": "lemma_reg",
            "reg_relation": "relation_reg",
            "reg_head": "head_reg",
        }

        for key, val in token.items():
            if key in sql_to_att_map.keys():
                if key in ["artificial", "insertion_id"] and not val:
                    continue

                val = str(val) if val is not None else ""
                word.set(sql_to_att_map[key], val)

        word.set("textpart", str(token.get("tp_n", "") or ""))
        word.set("line_n", str(token.get("line", "") or ""))
        word.set("lang", str(token.get("orig_lang", "") or ""))
        word.set("hand", str(token.get("hand", "") or ""))
        # word.set('tm_word_id', str(token.get('tm_word_id', '') or ''))
        word.set("id", str(token.get("n", "") or ""))

        s.append(word)

    return etree.tostring(
        root, encoding="utf-8", pretty_print=True, xml_declaration=False  # type: ignore
    )


@requires("editor")
async def release(request):
    texts = await db.fetch_all(
        """
        SELECT * 
          FROM `text` 
         WHERE orig_status = 3 
           AND reg_status = 3
        """
    )

    mem_zip = BytesIO()
    with zipfile.ZipFile(
        mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zip_file:
        for t in texts["result"]:
            file = await generate_treebank(t)
            zip_file.writestr(
                f'{t["series_type"]}/{t["series_name"]}/{t["name"]}',
                file,
            )

    return Response(
        mem_zip.getvalue(),
        media_type="application/zip",
        headers={"Content-disposition": f"attachment; filename=PapyGreekTreebanks.zip"},
    )


routes = [
    Route("/release", release),
]
