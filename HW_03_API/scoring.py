import hashlib
import json

TIME_OF_STORE = 60 * 60


def create_key_part(first_name, last_name, birthday, prefix):
    key_parts = [
        first_name or "",
        last_name or "",
        birthday.strftime("%d%m%Y") if birthday is not None else "",
    ]
    key = prefix + hashlib.md5("".join(key_parts).encode("utf-8")).hexdigest()
    return key


def get_score(store, phone, email, birthday=None, gender=None,
              first_name=None, last_name=None, prefix="uid:",
              time_of_store=TIME_OF_STORE):
    key = create_key_part(first_name, last_name, birthday, prefix)
    # try get from cache,
    # fallback to heavy calculation in case of cache miss
    score = store.cache_get(key) or 0
    if score:
        return score
    if phone:
        score += 1.5
    if email:
        score += 1.5
    if birthday and gender:
        score += 1.5
    if first_name and last_name:
        score += 0.5
    # cache for 60 minutes
    store.cache_set(key, score, time_of_store)
    return score


def get_interests(store, cid, prefix="i:"):
    r = store.get("%s%s" % (prefix, cid))
    return json.loads(r) if r else []
