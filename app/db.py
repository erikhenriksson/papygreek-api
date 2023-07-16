from operator import itemgetter
import natsort

import aiomysql
from . import config


class db:
    pool = None
    debug = False

    async def connect(self):
        self.pool = await aiomysql.create_pool(
            host=config.DB_HOST,
            port=int(config.DB_PORT),
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            db=config.DB_DB,
            autocommit=True,
            echo=True,
        )

    async def disconnect(self):
        if self.pool:
            self.pool.close()

    async def set_debug(self):
        self.debug = True

    async def q(self, method, *args, **kwargs):
        if not self.pool:
            return {"ok": False, "result": "No pool"}

        # To get executed query, use: cur._last_executed
        async def get_lastrowid(cur):
            return cur.lastrowid

        async def get_one(cur):
            return await cur.fetchone()

        async def get_first(cur):
            results = await cur.fetchall()
            return results[0] if results else []

        async def get_all(cur):
            results = await cur.fetchall()
            if nat := kwargs.get("natsort_by"):
                return natsort.natsorted(results, key=itemgetter(nat))
            return results

        sql = args[0]
        params = args[1] if len(args) > 1 else []

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                try:
                    if not self.debug:
                        await cur.execute(sql, params)
                        funcs = {
                            "exec": get_lastrowid,
                            "one": get_one,
                            "all": get_all,
                            "first": get_first,
                        }
                        return {"ok": True, "result": await funcs[method](cur)}
                    else:
                        print(f"Debugging.\nSql:\n{sql}\nParams:\n{params}")
                        return {"ok": True, "result": "Debug"}

                except Exception as e:
                    return {"ok": False, "result": f"sql: {sql[:100]}, error: {e}"}
                finally:
                    await cur.close()

    async def fetch_one(self, *args, **kwargs):
        return await self.q("one", *args, **kwargs)

    async def fetch_all(self, *args, **kwargs):
        return await self.q("all", *args, **kwargs)

    async def fetch_first(self, *args, **kwargs):
        return await self.q("first", *args, **kwargs)

    async def execute(self, *args, **kwargs):
        return await self.q("exec", *args, **kwargs)
