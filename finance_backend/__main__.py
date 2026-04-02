from __future__ import annotations

from wsgiref.simple_server import make_server

from finance_backend.app import create_app
from finance_backend.config import AppConfig


def main() -> None:
    config = AppConfig.from_env()
    app = create_app(config)
    with make_server(config.host, config.port, app) as server:
        print(
            f"Finance backend running on http://{config.host}:{config.port} "
            f"using database {config.database_path}"
        )
        server.serve_forever()


if __name__ == "__main__":
    main()
