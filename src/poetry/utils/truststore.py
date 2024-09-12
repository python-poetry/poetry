from __future__ import annotations

import typing

from cachecontrol import CacheControlAdapter
from requests.adapters import HTTPAdapter
from wassima import RUSTLS_LOADED
from wassima import generate_ca_bundle


if typing.TYPE_CHECKING:
    from urllib3 import HTTPConnectionPool


DEFAULT_CA_BUNDLE: str = generate_ca_bundle()


class WithTrustStoreAdapter(HTTPAdapter):
    """
    Inject the OS truststore in Requests.
    Certifi is still loaded in addition to the OS truststore for (strict) backward compatibility purposes.
    See https://github.com/jawah/wassima for more details.
    """

    def cert_verify(
        self,
        conn: HTTPConnectionPool,
        url: str,
        verify: bool | str,
        cert: str | tuple[str, str] | None,
    ) -> None:
        #: only apply truststore cert if "verify" is set with default value "True".
        #: RUSTLS_LOADED means that "wassima" is not the py3 none wheel and does not fallback on "certifi"
        #: if "RUSTLS_LOADED" is False then "wassima" just return "certifi" bundle instead.
        if (
            RUSTLS_LOADED
            and url.lower().startswith("https")
            and verify is True
            and hasattr(conn, "ca_cert_data")
        ):
            # url starting with https already mean that conn is a HTTPSConnectionPool
            # the hasattr is to make mypy happy.
            conn.ca_cert_data = DEFAULT_CA_BUNDLE

        # still apply upstream logic as before
        super().cert_verify(conn, url, verify, cert)  # type: ignore[no-untyped-call]


class CacheControlWithTrustStoreAdapter(CacheControlAdapter):
    """
    Same as WithTrustStoreAdapter but with CacheControlAdapter as its parent
    class.
    """

    def cert_verify(
        self,
        conn: HTTPConnectionPool,
        url: str,
        verify: bool | str,
        cert: str | tuple[str, str] | None,
    ) -> None:
        if (
            RUSTLS_LOADED
            and url.lower().startswith("https")
            and verify is True
            and hasattr(conn, "ca_cert_data")
        ):
            conn.ca_cert_data = DEFAULT_CA_BUNDLE

        super().cert_verify(conn, url, verify, cert)  # type: ignore[no-untyped-call]
