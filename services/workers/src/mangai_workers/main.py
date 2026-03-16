from __future__ import annotations

import argparse

from mangai_workers.config import get_settings
from mangai_workers.queue import process_next_job, run_worker_loop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MangAI worker service")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=("run", "once"),
        help="run keeps polling for queued jobs, once processes a single queued job",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()

    if args.command == "once":
        processed_job = process_next_job(settings)
        if processed_job is None:
            print("No queued jobs found.")
            return
        print(f"Processed job {processed_job['id']} with status {processed_job['status']}.")
        return

    print(
        f"{settings.app_name} running "
        f"(env={settings.environment}, data_dir={settings.data_dir}, poll={settings.poll_interval_seconds}s, "
        f"ocr={settings.ocr_provider}, translation={settings.translation_provider})"
    )
    run_worker_loop(settings)


if __name__ == "__main__":
    main()
