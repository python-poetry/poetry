def unique(l):
    used = set()

    return [x for x in l if x not in used and (used.add(x) or True)]
