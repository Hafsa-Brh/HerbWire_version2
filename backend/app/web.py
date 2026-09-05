import os
from collections.abc import Mapping

import uvicorn
from backend.app.core.settings import get_settings

DEFAULT_PORT = 8000


def runtime_port(environment: Mapping[str, str] | None = None) -> int:
    environment = environment or os.environ
    raw_port = environment.get("PORT", str(DEFAULT_PORT))
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ValueError("PORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    return port


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=runtime_port(),
        proxy_headers=settings.trust_proxy_headers,
        # Heroku dynos receive public traffic only through the router. Local runtime
        # never enables this trust by default.
        forwarded_allow_ips="*" if settings.trust_proxy_headers else "",
    )


if __name__ == "__main__":
    main()
