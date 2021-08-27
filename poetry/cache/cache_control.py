from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.cache import DictCache
from urllib3.util.retry import Retry


def CacheControl(
    sess,
    cache=None,
    cache_etags=True,
    serializer=None,
    heuristic=None,
    controller_class=None,
    adapter_class=None,
    cacheable_methods=None,
    max_retries=Retry(total=5, backoff_factor=1)
):

    cache = DictCache() if cache is None else cache
    adapter_class = adapter_class or CacheControlAdapter
    adapter = adapter_class(
        cache,
        cache_etags=cache_etags,
        serializer=serializer,
        heuristic=heuristic,
        controller_class=controller_class,
        cacheable_methods=cacheable_methods,
        max_retries=max_retries
    )
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)

    return sess
