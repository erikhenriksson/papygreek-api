from ..config import db

"""

Comment numbering for type 2:

    5 = Saved annotation


"""


async def insert_comment(text_id, user_id, type, text, layer):
    """
    Comment numbering (for type 2)
        1 = In progress
        2 = Rejected
        3 = Finalized
        6 = Submitted
        8 = Migrated
    """
    return await db.execute(
        """
        INSERT INTO comment (text_id, user_id, `type`, `text`, layer) 
        VALUES (%s, %s, %s, %s, %s)
    """,
        (text_id, user_id, type, text, layer),
    )


async def get_comment(comment_id):
    """Get one comment"""
    return await db.fetch_one(
        """
        SELECT comment.id AS comment_id, 
               `text` AS comment, 
               DATE_FORMAT(created, '%%Y-%%m-%%dT%%TZ') AS created_at, 
               DATE_FORMAT(created, '%%Y-%%m-%%dT%%TZ') AS updated_at, 
               user.name AS user
          FROM comment
               INNER JOIN user
               ON comment.user_id=user.id
         WHERE comment.id = %s
    """,
        (comment_id,),
    )
