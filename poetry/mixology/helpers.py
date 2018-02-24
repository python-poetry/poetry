def flat_map(iter, callable):
    if not isinstance(iter, (list, tuple)):
        yield callable(iter)
    else:
        for v in iter:
            for i in flat_map(v, callable):
                yield i
