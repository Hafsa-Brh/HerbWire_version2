import os
from collections.abc import Mapping

import uvicorn

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
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=runtime_port(),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
