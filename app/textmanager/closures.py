from ..config import db


async def update_text_closures(text_id):
    # Prune
    deleted = await db.execute(
        """
        DELETE 
          FROM token_closure 
         WHERE text_id = %s        
        """,
        (text_id,),
    )
    if not deleted["ok"]:
        return deleted

    # Insert closures for each layer
    for layer in ["orig", "reg"]:
        inserted = await db.execute(
            f"""
            INSERT INTO token_closure
                   (text_id,
                   ancestor,
                   descendant,
                   n,
                   depth,
                   layer)

            WITH RECURSIVE category_cte AS 
                 (SELECT {text_id} AS text_id,
                         id AS ancestor,
                         id AS descendant,
                         n,
                         sentence_n,
                         0 AS depth,
                         '{layer}' as layer
                    FROM token
                   WHERE text_id = {text_id}
                     AND ({layer}_head != n 
                         OR {layer}_head IS NULL)

                   UNION ALL

                   SELECT CTE.text_id,
                          CTE.ancestor  AS ancestor,
                          C.id AS descendant,
                          C.n,
                          C.sentence_n,
                          CTE.depth + 1 AS depth,
                          CTE.layer
                     FROM token AS C 
                          JOIN category_cte AS CTE
                          ON CTE.text_id = C.text_id 
                          AND C.{layer}_head = CTE.n 
                          AND C.sentence_n = CTE.sentence_n)
            
            SELECT text_id,
                   ancestor,
                   descendant,
                   n,
                   depth,
                   layer 
              FROM category_cte;
            """
        )
        if not inserted["ok"]:
            return inserted

    return {"ok": True, "result": ""}


async def cli():
    text_ids = await db.fetch_all(
        """
        SELECT id 
          FROM `text` 
         WHERE orig_status = 3 
           AND reg_status = 3
        """
    )

    # Prune closures of non-finalized texts
    await db.execute(
        """
        DELETE 
          FROM token_closure 
         WHERE text_id NOT IN = (%s)        
        """,
        (",".join([str(x["id"]) for x in text_ids["result"]]),),
    )

    for text_id in text_ids["result"]:
        result = await update_text_closures(text_id["id"])
        if not result["ok"]:
            print(result)
            break
