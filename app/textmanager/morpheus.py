from ..config import db, MORPHEUS_PATH

import xml.etree.ElementTree as ET


async def cli():
    # Get an iterable.
    context = ET.iterparse(MORPHEUS_PATH, events=("start", "end"))

    for index, (event, elem) in enumerate(context):
        # Get the root element.
        if index == 0:
            root = elem
        if event == "end" and elem.tag == "t":
            item = {}
            for child in elem:
                if child.tag == "f":
                    item["form"] = child.text
                elif child.tag == "b":
                    item["form_plain"] = child.text
                elif child.tag == "l":
                    item["lemma"] = child.text
                elif child.tag == "e":
                    item["lemma_plain"] = child.text
                elif child.tag == "p":
                    item["postag"] = child.text

            result = await db.execute(
                """
                INSERT INTO `morpheus`
                       (form, form_plain, lemma, lemma_plain, postag)
                VALUES (%(form)s, %(form_plain)s, %(lemma)s, %(lemma_plain)s, %(postag)s)
                """,
                (item),
            )
            if not result["ok"]:
                print(result)
                exit()
            root.clear()  # type: ignore
