from collections import namedtuple
import re
import unicodedata

from tqdm import tqdm

from ..config import db

Match = namedtuple("Match", "a b size")
plain = lambda x: "".join(
    [unicodedata.normalize("NFD", a)[0].lower() for a in x if a.isalpha() or a in ["_"]]
)


def plain_and_semiplain(t):
    t = re.sub(r"\$(?=.+)", "", t)
    t = re.sub(r"\*(.*?)\*", "", t)
    t = re.sub(r"(｢[^｣]+｣)+", "_", t)
    return plain(t), t


def find_longest_match(orig, reg_index, orig_start, orig_end, reg_start, reg_end):
    """Find longest matching sequence"""
    best_start, best_end, best_size = orig_start, reg_start, 0
    longest_match = {}

    # Iterate orig chars
    for orig_i in range(orig_start, orig_end):
        new_longest_match = {}

        # Get indexes in reg for orig char
        for reg_i in reg_index.get(orig[orig_i], []):
            # Index before the current block; pass
            if reg_i < reg_start:
                continue

            # Index over the block, break
            if reg_i >= reg_end:
                break

            # Get longest
            longest_size = new_longest_match[reg_i] = (
                longest_match.get(reg_i - 1, 0) + 1
            )

            # If this is now biggest, collect
            if longest_size > best_size:
                best_start = orig_i - longest_size + 1
                best_end = reg_i - longest_size + 1
                best_size = longest_size

        longest_match = new_longest_match

    return Match(best_start, best_end, best_size)


def get_matching_blocks(orig, reg, reg_index):
    """Get blocks that match"""
    orig_len = len(orig)
    reg_len = len(reg)

    # Start with the complete blocks given
    queue = [(0, orig_len, 0, reg_len)]
    matching_blocks = []
    while queue:
        orig_start, orig_end, reg_start, reg_end = queue.pop()

        match_start, match_end, size = x = find_longest_match(
            orig, reg_index, orig_start, orig_end, reg_start, reg_end
        )

        # If match of size > 0:
        if size:
            # Collect this match
            matching_blocks.append(x)

            if orig_start < match_start and reg_start < match_end:
                queue.append((orig_start, match_start, reg_start, match_end))
            if match_start + size < orig_end and match_end + size < reg_end:
                queue.append((match_start + size, orig_end, match_end + size, reg_end))

    # Sort by match start
    matching_blocks.sort()

    # Collapse adjacent same operation blocks
    i1 = j1 = k1 = 0
    non_adjacent = []
    for i2, j2, k2 in matching_blocks:
        # Is this block adjacent to i1, j1, k1?
        if i1 + k1 == i2 and j1 + k1 == j2:
            # Yes, so collapse them -- this just increases the length of
            # the first block by the length of the second, and the first
            # block so lengthened remains the block to compare against.
            k1 += k2
        else:
            # Not adjacent.  Remember the first block (k1==0 means it's
            # the dummy we started with), and make the second block the
            # new block to compare against.
            if k1:
                non_adjacent.append((i1, j1, k1))
            i1, j1, k1 = i2, j2, k2
    if k1:
        non_adjacent.append((i1, j1, k1))
    non_adjacent.append((orig_len, reg_len, 0))
    return list(map(Match._make, non_adjacent))


def get_changes(orig, reg, orig_full, reg_full):
    """Get the change deltas"""
    # Init vars
    orig_start = 0
    reg_start = 0
    answer = []
    reg_index = {}

    # Create index of chars in reg
    for i, elt in enumerate(reg):
        indices = reg_index.setdefault(elt, [])
        indices.append(i)

    # Get the matching sequences
    matching_blocks = get_matching_blocks(orig, reg, reg_index)

    # Iterate them
    for orig_end, reg_end, size in matching_blocks:
        tag = ""
        if orig_start < orig_end and reg_start < reg_end:
            tag = 2
        elif orig_start < orig_end:
            tag = -1
        elif reg_start < reg_end:
            tag = 1
        if tag:
            answer.append(
                {
                    "operation": tag,
                    "orig": orig_full[orig_start:orig_end],
                    "reg": reg_full[reg_start:reg_end],
                    "orig_bef": orig_full[:orig_start],
                    "orig_aft": orig_full[orig_end:],
                    "reg_bef": reg_full[:reg_start],
                    "reg_aft": reg_full[reg_end:],
                    "p_orig": orig[orig_start:orig_end],
                    "p_reg": reg[reg_start:reg_end],
                    "p_orig_bef": orig[:orig_start],
                    "p_orig_aft": orig[orig_end:],
                    "p_reg_bef": reg[:reg_start],
                    "p_reg_aft": reg[reg_end:],
                }
            )

        orig_start, reg_start = orig_end + size, reg_end + size

        if size:
            answer.append(
                {
                    "operation": 0,
                    "orig": orig_full[orig_end:orig_start],
                    "reg": "",
                    "orig_bef": orig_full[:orig_end],
                    "orig_aft": orig_full[orig_start:],
                    "reg_bef": reg_full[:reg_end],
                    "reg_aft": reg_full[reg_start:],
                    "p_orig": orig[orig_end:orig_start],
                    "p_reg": "",
                    "p_orig_bef": orig[:orig_end],
                    "p_orig_aft": orig[orig_start:],
                    "p_reg_bef": reg[:reg_end],
                    "p_reg_aft": reg[reg_start:],
                }
            )
    return answer


async def run_token(t):
    orig_plain, orig_full = plain_and_semiplain(t["orig_form"])
    reg_plain, reg_full = plain_and_semiplain(t["reg_form"])
    if reg_plain.replace("_", "") or orig_plain.replace("_", ""):
        changes = get_changes(orig_plain, reg_plain, orig_full, reg_full)

        for change in changes:
            if change["operation"] != 0:
                change["token_id"] = t["id"]
                change["text_id"] = t["text_id"]
                inserted = await db.execute(
                    """
                    INSERT INTO variation 
                           (token_id,	
                           text_id,
                           operation,	
                           orig,	
                           reg,	
                           reg_bef,	
                           reg_aft,
                           orig_bef,	
                           orig_aft,	
                           p_orig,	
                           p_reg,	
                           p_reg_bef,	
                           p_reg_aft,	
                           p_orig_bef,	
                           p_orig_aft)
                    VALUES (%(token_id)s, %(text_id)s, %(operation)s, %(orig)s, %(reg)s, %(reg_bef)s, %(reg_aft)s, %(orig_bef)s, %(orig_aft)s, %(p_orig)s, %(p_reg)s, %(p_reg_bef)s, %(p_reg_aft)s, %(p_orig_bef)s, %(p_orig_aft)s)
                    """,
                    (change),
                )
                if not inserted["ok"]:
                    return inserted

    return {"ok": True, "result": ""}


async def update_text_variations(text_id):
    # Prune
    deleted = await db.execute(
        """
        DELETE 
          FROM variation 
         WHERE text_id = %s;
        """,
        (text_id,),
    )
    if not deleted["ok"]:
        return deleted

    tokens = await db.fetch_all(
        """
        SELECT * 
          FROM token 
         WHERE text_id = %s
        """,
        (text_id,),
    )
    for t in tokens["result"]:
        result = await run_token(t)
        if not result["ok"]:
            return result

    return {"ok": True, "result": ""}


async def cli():
    text_ids = await db.fetch_all(
        """
        SELECT id 
          FROM `text`
        """
    )

    for text_id in tqdm(text_ids["result"]):
        result = await update_text_variations(text_id["id"])
        if not result["ok"]:
            print(result)
            break
