import tempfile
import pypandoc
import re
import asyncio
import json
import base64

from .search import get_sentence_tree_json
from starlette.routing import Route
from ..config import db
from ..response import JSONResponse
from ..utils import is_int
from starlette.authentication import requires


def synchronize_async_helper(to_await):
    async_response = []

    async def run_and_capture_result():
        r = await to_await
        async_response.append(r)

    loop = asyncio.get_event_loop()
    coroutine = run_and_capture_result()
    loop.run_until_complete(coroutine)
    return async_response[0]


async def update_bibliography():
    mds = await db.fetch_all(
        """
        SELECT md 
          FROM chapter 
         WHERE title != 'Bibliography'
    """
    )
    cit_list = []
    for md in mds["result"]:
        text = md["md"] or ""
        citations = re.findall("@[a-zA-Z0-9]+", text)
        if citations:
            cit_list += citations

    new_text = await mdtohtml("\n".join(cit_list), 0, 0)

    bib_html = f'<div id="main-bibliography">{new_text}</div>'

    await db.execute(
        """
        UPDATE chapter 
           SET html = %(html)s 
         WHERE title = 'Bibliography'
        """,
        {"html": bib_html},
    )


async def get_chapter_menu(chapter_id="NULL"):
    assert chapter_id == "NULL" or is_int(chapter_id)
    chapter_query = (
        "parent_id IS NULL" if chapter_id == "NULL" else f"id = {chapter_id}"
    )
    return await db.fetch_all(
        f"""
        WITH RECURSIVE cte AS 
             (SELECT id,
                     title,
                     parent_id,
                     seq,
                     CAST('' AS CHAR(1000)) AS path,
                     0 AS level,
                     IF(title = 'Bibliography', 1, 0) AS bib
                FROM chapter
               WHERE {chapter_query}
              
               UNION ALL
                
              SELECT chapter.id,
                     chapter.title,
                     chapter.parent_id,
                     chapter.seq,
                     concat(cte.path, '.', CAST(chapter.seq AS CHAR(1000))),
                     cte.level + 1,
                     IF(chapter.title = 'Bibliography', 1, 0)
                
                FROM cte
                     JOIN chapter 
                     ON chapter.parent_id = cte.id)

        SELECT id, 
               title, 
               parent_id,
               level, 
               seq, 
               path, 
               bib
          FROM cte
         ORDER BY bib, path, seq;
        """
    )


async def mdtohtml(md, chapter_id, path):
    menu_records = await get_chapter_menu()
    paths = {m["id"]: [m["path"][1:], m["title"]] for m in menu_records["result"]}
    tree_id = 1

    def convert_chapter_ref(match):
        nonlocal paths
        chapter_id = int(match.group(1))
        return f'<a href="/grammar/{chapter_id}" data-link data-url="grammar/{chapter_id}">{paths[chapter_id][0]}</a>'

    def convert_smyth_ref(match):
        smyth_id = match.group(1)
        smyth_name = match.group(2)
        return f'<a data-link-newtab href="/smyth/{smyth_id}" data-url="smyth/{smyth_id}">{smyth_name}</a>'

    def convert_search_ref(match):
        search_id = match.group(1)
        search_name = match.group(2)
        return f'<a data-link-newtab href="/search/{search_id}" data-url="search/{search_id}">{search_name}</a>'

    def convert_tree_ref(match):
        nonlocal tree_id

        doc_id = match.group(1)
        sentence_id = match.group(2)
        highlight = (match.group(3) or "").lstrip("-")
        edges = (match.group(4) or "").lstrip("-")
        layer = match.group(5)

        # Run the async function synchronously
        result = synchronize_async_helper(
            get_sentence_tree_json(doc_id, sentence_id, layer)
        )

        if result["ok"]:
            result["highlight_nodes"] = highlight
            result["highlight_edges"] = edges
            result["id"] = tree_id
            tree_id += 1
            b = base64.b64encode(json.dumps(result).encode("utf-8")).decode("utf-8")

            return f'<div style="height:300px; " data-treeid="{result["id"]}" class="sentence-tree tf-tree tf-result" data-json="{b}"></div>'
        return (
            f'<div class"info centered">Error: could not get tree from database</div>'
        )

    def convert_toc_ref(match):
        result = synchronize_async_helper(get_chapter_menu(chapter_id))

        if result["ok"] and len(result["result"]):
            tocHtml = "<div class='chapter-toc'><h3>Table of contents</h3>"
            for itm in result["result"][1:]:
                tocHtml += f"<div class='chapter-toc-item'><span data-chapterid='{itm['id']}' class='red chapter-link'>{path}{itm['path']} {itm['title']}</span></div>"
            tocHtml += "</div>"
            return tocHtml
        return ""

    def convert_document_ref(match):
        document_id = match.group(1)
        document_name = match.group(2)
        line_number = ""
        line_hash = ""
        try:
            if match.group(4):
                line_hash = f"#l-{match.group(4)}"
        except:
            pass

        try:
            if match.group(4):
                line_number = f", l. {match.group(4)}"
        except:
            pass

        return f'<a data-link-newtab href="/text/{document_id}{line_hash}" data-url="text/{document_id}{line_hash}">{document_name}{line_number}</a>'

    bib_record = await db.fetch_one("SELECT data FROM bibliography")
    library = bib_record["result"]["data"]

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w+") as t:
        t.write(library)
        t.seek(0)
        html = pypandoc.convert_text(
            md.strip(),
            "html",
            format="md",
            extra_args=["-C", "--bibliography", f"{t.name}"],
        )

        html = re.sub(r":chapter-([0-9]+):", convert_chapter_ref, html)
        html = re.sub(
            r":tree-([0-9]+)-([0-9]+)(-[0-9,]+)?(-[0-9,\/]+)?-(orig|reg):",
            convert_tree_ref,
            html,
        )
        html = re.sub(
            r":smyth-([A-Za-z0-9_\+\.]+)\(([^\)]+)\):", convert_smyth_ref, html
        )
        html = re.sub(
            r":search-([A-Za-z0-9_\+\.]+)\(([^\)]+)\):", convert_search_ref, html
        )
        html = re.sub(
            r":document-([0-9]+)\(([^\)]+)\)(\(([^\)]+)\))?:",
            convert_document_ref,
            html,
        )
        html = re.sub(
            r":toc:",
            convert_toc_ref,
            html,
        )

        return html


async def get_numbered_path(text_id):
    result = await db.fetch_all(
        """
        WITH RECURSIVE cte AS 
             (SELECT id, 
                     parent_id, 
                     seq
                FROM chapter
               WHERE id = %(text_id)s

               UNION ALL

              SELECT m.id, 
                     m.parent_id, 
                     m.seq
                FROM chapter AS m
                     INNER JOIN cte AS p 
                     ON m.id = p.parent_id
               WHERE m.id <> m.parent_id)
        
        SELECT id, 
               parent_id, 
               seq
          FROM cte
         WHERE parent_id IS NOT NULL;
        """,
        {"text_id": text_id},
    )

    ret = []

    if not result["result"]:
        return ""

    result["result"].reverse()

    for parent in result["result"]:
        ret.append(str(parent["seq"]))

    return ".".join(ret)


async def get_menu(request):
    return JSONResponse(await get_chapter_menu())


@requires("editor")
async def convert_md_to_html(request):
    q = await request.json()
    return JSONResponse({"html": await mdtohtml(q["md"], q["chapter_id"], q["path"])})


@requires("editor")
async def update_chapter(request):
    q = await request.json()
    md = (q["md"] or "").strip()
    chapter = (q["html"] or "").strip()
    chapter_id = q["id"]
    title = (q["title"] or "").strip()
    seq = q["seq"]
    parent_id = q["parent_id"] or None
    result = await db.execute(
        """
        UPDATE chapter 
            SET title = %(title)s, 
                md = %(md)s, 
                html = %(html)s, 
                seq = %(seq)s, 
                parent_id = %(parent_id)s 
            WHERE id = %(chapter_id)s
    """,
        {
            "md": md,
            "html": chapter,
            "title": title,
            "chapter_id": chapter_id,
            "seq": seq,
            "parent_id": parent_id,
        },
    )

    await update_bibliography()

    return JSONResponse(result)


@requires("editor")
async def add_chapter(request):
    insert_id = await db.execute(
        """
        INSERT INTO chapter (parent_id, title, seq, md, html) 
        SELECT 1, 'A New Chapter', MAX(seq)+1, 'Chapter text', '<p>Chapter text</p>'
          FROM chapter
         WHERE parent_id = 1
    """
    )

    await update_bibliography()

    return JSONResponse(insert_id)


@requires("editor")
async def delete_chapter(request):
    q = await request.json()
    chapter_id = q["id"]
    deleted = await db.execute(
        """
        DELETE 
          FROM chapter 
         WHERE id = %s
    """,
        (chapter_id,),
    )

    await update_bibliography()

    return JSONResponse(deleted)


async def get_chapter_by_id(request):
    result = await db.fetch_one(
        """
        SELECT id, 
               title, 
               seq, 
               md, 
               html, 
               parent_id 
          FROM chapter 
         WHERE id = %(id)s
    """,
        request.path_params,
    )

    path = await get_numbered_path(request.path_params["id"])

    result["result"]["path"] = path

    return JSONResponse(result)


routes = [
    Route("/{id:int}", get_chapter_by_id),
    Route("/add", add_chapter, methods=["POST"]),
    Route("/mdtohtml", convert_md_to_html, methods=["POST"]),
    Route("/save", update_chapter, methods=["POST"]),
    Route("/add", add_chapter),
    Route("/delete", delete_chapter, methods=["POST"]),
    Route("/get_menu", get_menu),
]
