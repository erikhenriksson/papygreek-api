import json
import traceback
import time

from unicodedata import normalize

from starlette.authentication import requires
from starlette.routing import Route

from ..config import db
from ..utils import cols, is_int, debug, to_int_or_none
from ..response import JSONResponse
from . import analyses

from pprint import pprint


def get_meta_filters(q):
    meta_filters = []
    additional_filters = ""
    values = {}
    if is_int(q["dna"]) and int(q["dna"]) < 1200:
        meta_filters.append(f'date_not_after <= {int(q["dna"])}')
    if is_int(q["dnb"]) and int(q["dnb"]) > -400:
        meta_filters.append(f'date_not_before >= {int(q["dnb"])}')

    if q["text-type"]:
        tt_filters = []
        tt_map = ["hypercategory", "category", "subcategory"]
        for i, tt in enumerate(q["text-type"].split("-")):
            if is_int(tt):
                tt_filters.append(f"{tt_map[i]}={int(tt)}")

        if tt_filters:
            tt_filter_inner = " AND ".join(tt_filters)
            meta_filters.append(
                f"""
                EXISTS (SELECT 1 
                          FROM aow_text_type 
                         WHERE text.id = aow_text_type.text_id 
                           AND token.aow_n = aow_text_type.aow_n 
                           AND {tt_filter_inner})
                """
            )

    if is_int(q["text-status"]):
        meta_filters.append(
            f"""
            EXISTS (SELECT 1 
                      FROM aow_text_type 
                     WHERE text.id = aow_text_type.text_id 
                       AND token.aow_n = aow_text_type.aow_n 
                       AND aow_text_type.status = {int(q["text-status"])})
            """
        )

    if is_int(q["person-id"]):
        certainty_filter = ""
        if is_int(q["person-certainty"]):
            if q["person-certainty"] == "1":
                certainty_filter = " AND uncertain = 1 "
            elif q["person-certainty"] == "0":
                certainty_filter = " AND uncertain != 1 "
        role_filter = ""
        if q["person-role"] in ["addressee", "author", "official", "writer"]:
            role = q["person-role"]
            role_filter = f" AND role = '{role}' "
        meta_filters.append(
            f"""
            EXISTS (SELECT 1 
                      FROM aow_person
                     WHERE text.id = aow_person.text_id 
                       AND token.aow_n = aow_person.aow_n 
                       AND person_id = {int(q["person-id"])}
                           {certainty_filter} {role_filter})
            """
        )

    if q["place-name"].strip():
        additional_filters += " AND text.place_name = %(place_name)s"
        values["place_name"] = q["place-name"].strip()

    if q["series-type"].strip():
        additional_filters += " AND text.series_type = %(series_type)s"
        values["series_type"] = q["series-type"].strip()

    # if q["regularization"]:
    #    additional_filters += " AND variation.regularization = 1"

    return meta_filters, additional_filters, values


async def search(request):
    def query_to_dict(tree):
        # Converts parameters into dict
        for el_i, el in enumerate(tree):
            to_dict = []
            for item in "".join(el["q"].split()).split(","):
                key_val = item.split("=")
                if key_val[0] == "*":
                    key_val = ["*", "*"]
                try:
                    key_val[1] = normalize("NFC", key_val[1])  # type: ignore
                except:
                    pass
                to_dict.append(key_val)
            tree[el_i]["q"] = dict(to_dict)
            if "children" in el:
                query_to_dict(el["children"])
        return tree

    # Get start time
    startTime = time.time()

    # Get the query
    q = await request.json()
    layer = q["layer"]
    assert layer in ["orig", "reg"]

    # Get metadata filters
    meta_filters, additional_filters, values = get_meta_filters(q)

    n_index = {}

    result_nodes = set()

    def get_leaf_query(query, values, prefix="root"):
        # debug(
        #    f"Entering get_leaf_query, query={query}, values={values}, prefix={prefix}"
        # )

        def get_variation_query(var_query_string):
            ret = {
                "operation": "0",
                "orig_bef": [],
                "orig": [],
                "reg": [],
                "orig_aft": [],
            }

            bef_split = var_query_string.split(">")
            ret["orig_bef"] = bef_split[0] if len(bef_split) >= 2 else []
            af_split = bef_split[-1].split("<")
            ret["orig_aft"] = af_split[1] if len(af_split) >= 2 else []
            center = af_split[0]

            if ("+" in center and "-" not in center) or (
                "+" not in center and "-" not in center
            ):
                ret["operation"] = "1"
                ret["reg"] = center.replace("+", "")
            elif "-" in center and "+" not in center:
                ret["operation"] = "-1"
                ret["orig"] = center.replace("-", "")
            elif "-" in center and "+" in center:
                ret["operation"] = "2"
                ret["orig"] = center.split("-")[1].split("+")[0]
                ret["reg"] = center.split("+")[1].split("-")[0]
            assert all(k in cols("variation") for k in ret.keys())
            return {
                k: v.replace("－", "-").replace("＋", "+") for k, v in ret.items() if v
            }

        def validate_token_cols(column, layer):
            if column == "form":
                column = f"{layer}_plain"
            elif column in ["postag", "relation", "head", "lemma", "lemma_plain"]:
                column = f"{layer}_{column}"
            elif column in ["text_id", "*"]:
                column = column
            else:
                raise NotImplementedError

            return column

        if "*" in query.keys():
            # If searching for anything (*), limit to finalized treebanks
            if prefix == "root":
                where = "INNER JOIN text ON token.text_id = text.ID AND text.orig_status=3 AND text.reg_status=3"
            else:
                where = "1=1"
            return (where, values, "", "")

        where = []
        variation_join = ""
        rdg_join = ""
        for col, val in query.items():
            operator = "REGEXP" if len(col.split("regex:")) == 2 else "LIKE"
            col = col.split("regex:")[-1]

            if col == "form" and ("<" in val or ">" in val or "+" in val or "-" in val):
                variation_query = get_variation_query(val)
                for k2, v2 in variation_query.items():
                    values[f"{prefix}_{k2}"] = v2
                q = " AND ".join(
                    [
                        f'variation.{k} {operator if k!="operation" else "="} %({prefix}_{k})s'
                        for k, v in variation_query.items()
                    ]
                )
                q = f"({q})"
                variation_join = "1"
            elif col == "rdg":
                values[f"{prefix}_{col}"] = val
                q = f" token_rdg.plain = %({prefix}_{col})s "
                rdg_join = "1"
            else:
                if col == "order":
                    continue
                values[f"{prefix}_{col}"] = val
                q = f"{validate_token_cols(col, layer)} {operator} %({prefix}_{col})s"

            where.append(q)
        where = " AND ".join(where)

        return where, values, variation_join, rdg_join

    async def tree_query(root, leaves, root_query=0):
        # debug(
        #    f"Entering tree_query {'(root version)' if root_query else ''} with root={root}, leaves={leaves}"
        # )

        # Build depth query
        def depth_q(d):
            try:
                d = f"={int(d)}"
            except:
                d = ">0"
            return d

        # Extract special parameters (depth)
        depths = [depth_q(x.pop("depth")) if "depth" in x else "=1" for x in leaves]

        wheres = []
        this_values = {}
        leafs_variation_join = []
        leafs_rdg_join = []

        # debug(f"Now, we enumerate leaves to populate vars")

        for leaf_i, leaf in enumerate(leaves):
            where, this_values, variation_join, rdg_join = get_leaf_query(
                leaf, this_values, str(leaf_i)
            )

            leafs_variation_join.append(variation_join)
            leafs_rdg_join.append(rdg_join)
            wheres.append(where)

        # debug(
        #    f"Finished leaf enumeration. Result: leafs_var_join={leafs_variation_join}, leafs_rdg_join={leafs_rdg_join}, wheres={wheres}, this_values={this_values}"
        # )

        if root_query:
            root, values, root_variation_join, root_rdg_join = get_leaf_query(
                root, this_values
            )
            if not root.startswith("INNER"):
                root = f"WHERE ({root})"
            ancestor_filter = f'SELECT token.id FROM token {"JOIN variation ON token.id=variation.token_id" if root_variation_join else ""} {"JOIN token_rdg ON token_rdg.token_id=token.id" if root_rdg_join else ""} {root}'
            # debug(f"Ancestor filter (root version) is {ancestor_filter}")
        else:
            ancestor_filter = ",".join(root)
            # debug(f"Ancestor filter is {ancestor_filter}")

        descendant_select = ",".join(
            [f"L{i}.descendant as L{i}, L{i}.n as L{i}n" for i in range(len(leaves))]
            # [f"L{i}.descendant as L{i}" for i in range(len(leaves))]
        )
        descendant_joins = "\n".join(
            [
                f'JOIN token_closure L{i} ON R.ancestor = L{i}.ancestor AND L{i}.depth {depths[i]} AND L{i}.descendant IN (SELECT token.id FROM token {"JOIN variation ON token.id=variation.token_id" if leafs_variation_join[i] else ""} {"JOIN token_rdg ON token_rdg.token_id=token.id" if leafs_rdg_join[i] else ""} WHERE ({x}))'
                for i, x in enumerate(wheres)
            ]
        )

        # The following makes sure that if the leaves have the same parameters, they are all included
        # using the MySQL <> syntax (= require leaves to be different)
        require_distinct_leaves = ""
        if len(leaves) > 1:
            leaves_n = range(len(leaves))
            require_distinct_leaves = "AND (" + (
                " AND ".join(
                    f"L{i}.descendant <> L{j}.descendant"
                    for i in leaves_n
                    for j in leaves_n
                    if i < j
                )
                + ")"
            )

        descendant_groupers = ",".join([f"L{i}" for i in range(len(leaves))])
        group_by = f"R, {descendant_groupers}" if descendant_groupers else "R"

        sql = f"""
            SELECT R.ancestor as R, Rn.n as RN, {descendant_select}
            FROM token_closure R
            {descendant_joins}
            JOIN token_closure Rn ON R.ancestor=Rn.descendant
            WHERE R.ancestor IN ({ancestor_filter})
            {require_distinct_leaves}
            GROUP BY {group_by}
            """
        # debug(f"This tree query was built: '{sql}, values={this_values}'")
        print(sql)
        closure = await db.fetch_all(sql, this_values)
        if closure["ok"]:
            # debug(
            #    f'Got {len(closure["result"])} results. Keys are: {closure["result"][0].keys() if closure["result"] else "()"}'
            # )
            # debug(closure["result"])
            data = [list(x.values()) for x in closure["result"]]
            closure = [
                [sublist[i] for i in range(0, len(sublist), 2)] for sublist in data
            ]
            closure_orders = [
                [sublist[i] for i in range(1, len(sublist), 2)] for sublist in data
            ]

            # print(f"closure is {closure}")

        else:
            raise Exception(closure["result"])
        # debug("")
        return closure, closure_orders

    """
    async def traverse(tree, ancestor_and_descendant_ids, level):

        for el_i, el in enumerate(tree):
            if not "children" in el:
                level -= 1
                return ancestor_and_descendant_ids
            else:
                ancestor_ids = [str(x[el_i + 1]) for x in ancestor_and_descendant_ids]
                this_ancestor_and_descendant_ids, _ = await tree_query(
                    ancestor_ids, [x["q"] for x in el["children"]]
                )
                if not this_ancestor_and_descendant_ids:
                    return []

                ancestor_and_descendant_ids = await traverse(
                    el["children"], this_ancestor_and_descendant_ids, level + 1
                )

                this_ancestor_ids = [x[0] for x in this_ancestor_and_descendant_ids]
                ancestor_and_descendant_ids = [
                    x
                    for x in ancestor_and_descendant_ids
                    if x[el_i + 1] in this_ancestor_ids
                ]

        return ancestor_and_descendant_ids
    """

    token_id_n_map = {}

    async def traverse(tree, ancestor_and_descendant_ids, level):
        nonlocal token_id_n_map

        for el_i, el in enumerate(tree):
            if "children" in el:
                # NOTE: the following has str(x[el_i + 1]) because index 0 are roots;
                # el_i + 1 is the new ancestor

                ancestor_ids = [str(x[el_i + 1]) for x in ancestor_and_descendant_ids]
                (
                    this_ancestor_and_descendant_ids,
                    this_ancestor_and_descendant_ns,
                ) = await tree_query(ancestor_ids, [x["q"] for x in el["children"]])
                if not this_ancestor_and_descendant_ids:
                    return []

                for r_i, taadi in enumerate(this_ancestor_and_descendant_ids):
                    taadn = this_ancestor_and_descendant_ns[r_i]
                    for token_id, n in zip(taadi, taadn):
                        if token_id not in token_id_n_map:
                            token_id_n_map[token_id] = n

                this_ancestor_and_descendant_ids = await traverse(
                    el["children"], this_ancestor_and_descendant_ids, level + 1
                )

                """
                The following code is important.
                """
                # First, get new ancestor list
                this_ancestor_ids = [x[0] for x in this_ancestor_and_descendant_ids]

                # THE MAIN FILTERING CODE: retain just those ancestor_and_descendant_ids
                # where the current ancestor (el_i + 1) was returned by the tree query
                # (this_ancestor_and_descendant_ids)
                ancestor_and_descendant_ids = [
                    x
                    for x in ancestor_and_descendant_ids
                    if x[el_i + 1] in this_ancestor_ids
                ]
        for el_i, el in enumerate(tree):
            el["ids"] = []
            for ids in ancestor_and_descendant_ids:
                el["ids"].append(
                    {
                        "ancestor": ids[0],
                        "descendant": ids[el_i + 1],
                        "n": token_id_n_map[ids[el_i + 1]],
                    }
                )

        return ancestor_and_descendant_ids

    def get_final_sql(
        variation_join, rdg_join, where, meta_filters, additional_filters
    ):
        if variation_join:
            variation_join = "INNER JOIN variation ON variation.token_id = token.id"
        return f"""
            SELECT 
                token.text_id, 
                text.name, 
                CAST(NULLIF(text.date_not_after, '') AS SIGNED) AS date_not_after,
                CAST(NULLIF(text.date_not_before, '') AS SIGNED) AS date_not_before,
                text.place_name, 
                token.id, 
                token.n, 
                token.aow_n,
                token.sentence_n, 
                token.line, 
                token.hand, 
                token.orig_form, 
                token.orig_lemma, 
                token.orig_postag, 
                token.orig_relation, 
                token.orig_head, 
                token.reg_form, 
                token.reg_lemma,
                token.reg_postag, 
                token.reg_relation, 
                token.reg_head, 
                artificial,
                text.{layer}_status,
                GROUP_CONCAT(token_rdg.form) AS rdgs,
                {"1 as regularization" if not variation_join else "variation.regularization"}
            FROM 
                token 
            LEFT JOIN token_rdg ON token_rdg.token_id = token.id
            {variation_join}
            JOIN 
                `text` 
            ON 
                token.text_id=`text`.id
            WHERE {where}
            {("AND " + " AND ".join(meta_filters)) if meta_filters else ""}
            {additional_filters}
            GROUP BY token.id
        """

    orders = []

    try:
        # Get the parameters as dict
        query = query_to_dict([q["q"]])[0]
        # Plain search (non-recursive)
        if not "children" in query:
            where, values, variation_join, rdg_join = get_leaf_query(
                query["q"], values, "flat"
            )

        # Tree search (recursive)
        else:
            debug("This is a tree search.")

            # Get initial ancestor and descendant ids
            ancestor_and_descendant_ids, ancestor_and_descendant_ns = await tree_query(
                query["q"], [x["q"] for x in query["children"]], 1
            )

            for r_i, aadi in enumerate(ancestor_and_descendant_ids):
                aadn = ancestor_and_descendant_ns[r_i]
                for token_id, n in zip(aadi, aadn):
                    if token_id not in token_id_n_map:
                        token_id_n_map[token_id] = n

            # Traverse result will be the filtered ancestor and descendant ids
            result = await traverse(
                query["children"],
                ancestor_and_descendant_ids,
                1,
            )

            if not result:
                return JSONResponse({"ok": True, "result": []})

            query["ids"] = list(set([x[0] for x in result]))

            def build_paths(node, current_path, paths):
                if "children" not in node:
                    paths.append(current_path)
                    return

                # Iterate through the children nodes
                for child in node.get("children", []):
                    # Iterate through the ids of the current child
                    for id_entry in child["ids"]:
                        # Check if the current ancestor is part of the existing path
                        if current_path[-1]["id"] == id_entry["ancestor"]:
                            # If so, continue building the path recursively
                            build_paths(
                                child,
                                current_path
                                + [
                                    {
                                        "id": id_entry["descendant"],
                                        "order": child["q"].get("order", None),
                                        "n": token_id_n_map[id_entry["descendant"]],
                                    }
                                ],
                                paths,
                            )

            filtered_result = []
            for root_id in query["ids"]:
                final_paths = []
                build_paths(
                    query,
                    [
                        {
                            "id": root_id,
                            "order": query["q"].get("order", None),
                            "n": token_id_n_map[root_id],
                        }
                    ],
                    final_paths,
                )
                flattened_list = []

                for sublist in final_paths:
                    for item in sublist:
                        if item not in flattened_list:
                            flattened_list.append(item)

                # Filter items with an "order" value
                filtered_data = [item for item in flattened_list if item["order"]]
                if not filtered_data or len(filtered_data) == 1:
                    filtered_result.append(str(root_id))
                    continue

                # Sort by "order" value
                sorted_data = sorted(filtered_data, key=lambda x: int(x["order"]))

                # Check if "n" values are in the same order as "order" values
                if all(
                    sorted_data[i]["n"] <= sorted_data[i + 1]["n"]
                    for i in range(len(sorted_data) - 1)
                ):
                    filtered_result.append(str(root_id))

            if not filtered_result:
                return JSONResponse({"ok": True, "result": {"data": []}})

            # Here we use the final filtered list of root ids
            where = f"token.id IN ({','.join(filtered_result)})"
            variation_join = ""
            rdg_join = ""

        sql = get_final_sql(
            variation_join, rdg_join, where, meta_filters, additional_filters
        )
        debug(f"final_sql: {sql}")
        result = await db.fetch_all(sql, values)

        if result["ok"]:
            executionTime = time.time() - startTime
            debug("Execution time in seconds: " + str(executionTime))

            date_frequencies = analyses.get_text_date_frequencies(result["result"])

            return JSONResponse(
                {
                    "ok": True,
                    "result": {
                        "data": result["result"],
                        "date_frequencies": date_frequencies,
                    },
                }
            )
        else:
            return JSONResponse(
                {"ok": False, "detail": "Something went wrong", "error": ""}
            )

    except Exception as error:
        debug(traceback.format_exc())
        e = error.__class__.__name__
        detail = "Server error"
        if e == "NotImplementedError":
            detail = "Some fields are incorrect. Check the <span class='help-link'>user guide</span>. "
        elif e == "ResourceWarning":
            detail = "No results"
        elif e == "ValueError":
            detail = "Please enter some search parameters ([key]=[value])."
        return JSONResponse(
            {"ok": False, "detail": detail, "error": error, "result": "No results"},
            status_code=200,
        )


@requires("user")
async def check_if_search_exists(request):
    q = await request.json()
    db_searches = await db.fetch_all(
        """
        SELECT id 
          FROM search 
         WHERE user_id = %(user)s 
           AND name = %(name)s
        """,
        {"user": request.user.id, "name": q["name"]},
    )
    if db_searches["ok"]:
        return JSONResponse({"ok": 1, "result": db_searches["result"]})


@requires("user")
async def delete(request):
    q = await request.json()
    db_searches = await db.fetch_all(
        """
        SELECT id 
          FROM search 
         WHERE user_id = %(user)s 
           AND id = %(id)s
        """,
        {"user": request.user.id, "id": q["id"]},
    )
    if db_searches["result"]:
        deleted = await db.execute(
            """
            DELETE
            FROM search 
            WHERE user_id = %(user)s 
            AND id = %(id)s
            """,
            {"user": request.user.id, "id": q["id"]},
        )
        if deleted["ok"] == 1:
            return JSONResponse({"ok": True})
    return JSONResponse({"ok": False})


@requires("user")
async def save(request):
    q = await request.json()
    db_searches = await db.fetch_all(
        """
        SELECT id 
          FROM search 
         WHERE user_id = %(user)s 
           AND name = %(name)s
        """,
        {"user": request.user.id, "name": q["name"]},
    )

    if db_searches["result"]:
        await db.execute(
            """
            UPDATE search 
               SET query = %(query)s, 
                   public = %(public)s 
             WHERE id = %(id)s
            """,
            {
                "query": json.dumps(q["q"]),
                "id": db_searches["result"][0]["id"],
                "public": q["public"],
            },
        )

        return JSONResponse(
            {"ok": True, "result": {"id": db_searches["result"][0]["id"], "new": 0}}
        )

    else:
        new_search_id = await db.execute(
            """
            INSERT INTO search (query, name, user_id, public) 
            VALUES (%(query)s, %(name)s, %(user)s, %(public)s)
            """,
            {
                "query": json.dumps(q["q"]),
                "name": q["name"],
                "user": request.user.id,
                "public": q["public"],
            },
        )

        return JSONResponse(
            {"ok": True, "result": {"id": new_search_id["result"], "new": 1}}
        )


@requires("user")
async def get_user_searches(request):
    searches = await db.fetch_all(
        """
        SELECT * 
          FROM search 
         WHERE user_id = %(user)s 
         ORDER BY name
        """,
        {"user": request.user.id},
    )
    return JSONResponse(searches)


@requires("user")
async def get_other_users_public_searches(request):
    searches = await db.fetch_all(
        """
        SELECT search.id, search.name, user.name as user_name
          FROM search 
          JOIN user ON search.user_id = user.id
         WHERE public = 1
           AND search.user_id != %(user)s 
         ORDER BY user.name, search.name
        """,
        {"user": request.user.id},
    )
    return JSONResponse(searches)


async def get_search_by_id(request):
    if type(request.user).__name__ == "GoogleUser":
        db_searches = await db.fetch_all(
            """
            SELECT * 
              FROM search 
             WHERE (user_id = %(user)s or public = 1)
               AND id = %(id)s
            """,
            {"user": request.user.id, "id": request.path_params["id"]},
        )
    else:
        db_searches = await db.fetch_all(
            """
            SELECT * 
              FROM search 
             WHERE id = %(id)s 
               AND public = 1
            """,
            {"id": request.path_params["id"]},
        )
    if db_searches:
        return JSONResponse(db_searches)
    else:
        return JSONResponse({"ok": True, "result": []})


async def get_sentence_tree_json(text_id, sentence_n, layer):
    assert layer in ["orig", "reg"]
    data = await db.fetch_all(
        f"""
        SELECT token.id, 
               token.n, 
               {layer}_head as head, 
               {layer}_form as form,
               insertion_id,
               artificial,
               {layer}_relation as relation,
               {layer}_postag as postag,
               IFNULL(NULLIF(CAST(SUBSTRING(insertion_id, 1, 4) AS UNSIGNED), ''), token.n) AS sorter1,
               IFNULL(NULLIF(SUBSTRING(insertion_id, 5, 20), ''), '') AS sorter2,
               token_closure.depth
          FROM token 
          LEFT JOIN token_closure
            ON token.id = token_closure.descendant AND token_closure.layer = "{layer}"
          LEFT JOIN token_closure tc2 ON tc2.descendant = token_closure.descendant AND tc2.depth > token_closure.depth
         WHERE tc2.descendant IS NULL
           AND sentence_n = %(sentence_n)s
           AND token.text_id = %(text_id)s
         ORDER BY depth DESC, sorter1, sorter2;
        """,
        {"text_id": text_id, "sentence_n": sentence_n},
    )

    return data


async def get_sentence_tree(request):
    q = await request.json()
    text_id = q["text_id"]
    sentence_n = q["sentence_n"]
    layer = q["layer"]
    json = await get_sentence_tree_json(text_id, sentence_n, layer)
    return JSONResponse({"ok": True, "result": json})


routes = [
    Route("/", search, methods=["POST"]),
    Route("/save", save, methods=["POST"]),
    Route("/delete", delete, methods=["POST"]),
    Route("/check_if_exists", check_if_search_exists, methods=["POST"]),
    Route("/get_saved", get_user_searches),
    Route("/get_others_public", get_other_users_public_searches),
    Route("/get_by_id/{id:int}", get_search_by_id),
    Route("/get_sentence_tree", get_sentence_tree, methods=["POST"]),
]
