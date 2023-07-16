import os

from ..config import db, DB_DB, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, BACKUP_DIR


async def cli():
    tables = await db.fetch_all(
        """
        SELECT table_name 
          FROM information_schema.tables
         WHERE table_schema = %s
        """,
        (DB_DB,),
    )

    for table in tables["result"]:
        table = table["TABLE_NAME"]
        backup_file_path = f"{BACKUP_DIR}/{table}.sql"
        mysqldump_cmd = f"mysqldump -h {DB_HOST} -u {DB_USER} -P{DB_PORT} -p{DB_PASSWORD} {DB_DB} {table} > {backup_file_path}"
        gzip_cmd = f"gzip --force {backup_file_path}"
        os.system(mysqldump_cmd)
        os.system(gzip_cmd)

    os.chdir(f"{BACKUP_DIR}")

    git_add = "git add ."
    git_commit = "git commit -m 'update'"
    git_push = "git push origin"

    os.system(git_add)
    os.system(git_commit)
    os.system(git_push)
