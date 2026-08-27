"""Part B - Weekly Lichess tournament automation with dry-run simulation mode."""
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd
import yaml
from dotenv import load_dotenv

from src.api_client import LichessAPIError, LichessClient
from src.utils import next_occurrence, parse_weekday, setup_logging

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "logs" / "tournament_automation.log"
DATA_DIR = ROOT / "output" / "data"


def parse_args():
    parser = argparse.ArgumentParser(description="Automate the weekly Lichess tournament schedule")
    parser.add_argument("--config", default=str(ROOT / "config" / "tournaments.yaml"), help="Path to the YAML schedule")
    parser.add_argument("--execute", action="store_true", help="Actually create tournaments via the API (default is dry-run)")
    return parser.parse_args()


def load_schedule(config_path: Path) -> List[dict]:
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("tournaments", [])


def build_payload(entry: dict, start_dt: datetime) -> dict:
    return {
        "name": entry["name"],
        "clockTime": entry["clock_time"],
        "clockIncrement": entry["clock_increment"],
        "minutes": entry["duration_minutes"],
        "waitMinutes": entry.get("wait_minutes", 5),
        "startDate": int(start_dt.timestamp() * 1000),
        "variant": entry.get("variant", "standard"),
        "rated": str(entry.get("rated", True)).lower(),
    }


def run(config_path: Path, dry_run: bool, logger) -> pd.DataFrame:
    schedule = load_schedule(config_path)
    now = datetime.now(timezone.utc)
    client = None if dry_run else LichessClient(token=os.getenv("LICHESS_TOKEN"))

    results = []
    for entry in schedule:
        name = entry.get("name", "unnamed")
        try:
            weekday = parse_weekday(entry["weekday"])
            hour, minute = (int(x) for x in entry["time"].split(":"))
            start_dt = next_occurrence(weekday, hour, minute, now)

            if start_dt < now:
                logger.info("Skipping '%s': scheduled start %s (UTC) already passed", name, start_dt.isoformat())
                results.append({"name": name, "scheduled_start_utc": start_dt, "status": "skipped", "detail": "start time already passed"})
                continue

            payload = build_payload(entry, start_dt)

            if dry_run:
                logger.info("[DRY-RUN] Would create '%s' at %s (UTC) | payload=%s", name, start_dt.isoformat(), payload)
                results.append({"name": name, "scheduled_start_utc": start_dt, "status": "dry-run", "detail": "simulated, not sent to API"})
                continue

            response = client.create_tournament(payload)
            tournament_id = response.get("id", "?")
            logger.info("Created tournament '%s' (id=%s) starting %s (UTC)", name, tournament_id, start_dt.isoformat())
            results.append({"name": name, "scheduled_start_utc": start_dt, "status": "created", "detail": tournament_id})

        except LichessAPIError as exc:
            logger.error("API error creating '%s': %s", name, exc)
            results.append({"name": name, "scheduled_start_utc": None, "status": "failed", "detail": str(exc)})
        except Exception as exc:  # a single bad entry must not stop the rest of the run
            logger.error("Unexpected error processing '%s': %s", name, exc)
            results.append({"name": name, "scheduled_start_utc": None, "status": "failed", "detail": str(exc)})

    return pd.DataFrame(results)


def main():
    load_dotenv()
    args = parse_args()
    logger = setup_logging(LOG_FILE, "tournament_automation")
    dry_run = not args.execute

    logger.info("Starting tournament automation run (dry_run=%s, config=%s)", dry_run, args.config)
    report_df = run(Path(args.config), dry_run, logger)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = DATA_DIR / f"tournament_run_{timestamp}.csv"
    report_df.to_csv(report_path, index=False)
    logger.info("Run report saved to %s", report_path)

    summary = report_df["status"].value_counts().to_dict() if not report_df.empty else {}
    logger.info("Run summary: %s", summary)


if __name__ == "__main__":
    main()
