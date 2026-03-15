from __future__ import annotations

from mangai_workers.config import get_settings


def main() -> None:
    settings = get_settings()
    print(
        f"{settings.app_name} bootstrap ready "
        f"(env={settings.environment}, data_dir={settings.data_dir}, poll={settings.poll_interval_seconds}s)"
    )


if __name__ == "__main__":
    main()
