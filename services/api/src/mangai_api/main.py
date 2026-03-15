import uvicorn

from mangai_api.app import app
from mangai_api.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "mangai_api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
    )


if __name__ == "__main__":
    main()
