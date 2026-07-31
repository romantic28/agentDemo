"""应用启动入口"""

import uvicorn

from shared.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "services.gateway:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.app_log_level.lower(),
    )


if __name__ == "__main__":
    main()
