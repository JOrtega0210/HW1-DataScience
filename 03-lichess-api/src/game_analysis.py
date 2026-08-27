"""Part A - Lichess game analysis: fetch games, compute stats, plot and export to CSV."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv

from src.api_client import LichessAPIError, LichessClient
from src.utils import game_result, setup_logging

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "logs" / "game_analysis.log"
DEMO_FIXTURE = ROOT / "fixtures" / "sample_games.ndjson"
DEMO_USERNAME = "DemoPlayer"


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze a Lichess player's game history")
    parser.add_argument("--username", default=os.getenv("LICHESS_USERNAME"), help="Lichess username to analyze")
    parser.add_argument("--max-games", type=int, default=int(os.getenv("MAX_GAMES", "100")), help="Number of games to retrieve")
    parser.add_argument("--output-dir", default=str(ROOT / "output"), help="Base output directory")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the full pipeline against local sample data instead of calling the live API "
        "(useful to verify/demo the analysis without spending API quota)",
    )
    return parser.parse_args()


def load_demo_games(fixture_path: Path) -> Iterable[dict]:
    with open(fixture_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def fetch_games_dataframe(games: Iterable[dict], username: str, logger) -> pd.DataFrame:
    rows = []

    for game in games:
        players = game.get("players", {})
        white = players.get("white", {})
        black = players.get("black", {})
        white_name = (white.get("user") or {}).get("name", "")
        black_name = (black.get("user") or {}).get("name", "")

        if white_name.lower() == username.lower():
            color, player, opponent = "white", white, black
        elif black_name.lower() == username.lower():
            color, player, opponent = "black", black, white
        else:
            continue

        opening = game.get("opening") or {}
        rows.append(
            {
                "id": game.get("id"),
                "date": datetime.fromtimestamp(game.get("createdAt", 0) / 1000, tz=timezone.utc),
                "speed": game.get("speed"),
                "variant": game.get("variant"),
                "rated": game.get("rated"),
                "status": game.get("status"),
                "color": color,
                "result": game_result(color, game.get("winner")),
                "player_rating": player.get("rating"),
                "rating_diff": player.get("ratingDiff"),
                "opponent": (opponent.get("user") or {}).get("name", "?"),
                "opponent_rating": opponent.get("rating"),
                "opening_eco": opening.get("eco"),
                "opening_name": opening.get("name"),
            }
        )

    logger.info("Retrieved %s games belonging to '%s'", len(rows), username)
    return pd.DataFrame(rows)


def build_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = {"total_games": len(df)}
    if df.empty:
        return pd.DataFrame([{"metric": k, "value": v} for k, v in stats.items()])

    total = len(df)
    result_counts = df["result"].value_counts()
    for result in ["win", "loss", "draw"]:
        count = int(result_counts.get(result, 0))
        stats[f"result_{result}_count"] = count
        stats[f"result_{result}_pct"] = round(count / total * 100, 2)

    stats["avg_player_rating"] = round(df["player_rating"].mean(), 1)
    stats["min_player_rating"] = int(df["player_rating"].min())
    stats["max_player_rating"] = int(df["player_rating"].max())

    df_sorted = df.sort_values("date")
    stats["rating_first"] = int(df_sorted["player_rating"].iloc[0])
    stats["rating_last"] = int(df_sorted["player_rating"].iloc[-1])
    stats["rating_change"] = stats["rating_last"] - stats["rating_first"]

    for color in ["white", "black"]:
        sub = df[df["color"] == color]
        win_rate = (sub["result"] == "win").mean() * 100 if len(sub) else 0
        stats[f"games_{color}"] = len(sub)
        stats[f"winrate_{color}_pct"] = round(win_rate, 2)

    for mode, count in df["speed"].value_counts().items():
        sub = df[df["speed"] == mode]
        win_rate = (sub["result"] == "win").mean() * 100
        stats[f"games_mode_{mode}"] = int(count)
        stats[f"winrate_mode_{mode}_pct"] = round(win_rate, 2)

    # Innovation: performance vs stronger/weaker opponents
    df_valid = df.dropna(subset=["opponent_rating", "player_rating"])
    if not df_valid.empty:
        diff = df_valid["player_rating"] - df_valid["opponent_rating"]
        underdog = df_valid[diff < -20]
        favorite = df_valid[diff > 20]
        for label, sub in [("underdog", underdog), ("favorite", favorite)]:
            win_rate = (sub["result"] == "win").mean() * 100 if len(sub) else 0
            stats[f"winrate_as_{label}_pct"] = round(win_rate, 2)
            stats[f"games_as_{label}"] = len(sub)

    return pd.DataFrame([{"metric": k, "value": v} for k, v in stats.items()])


def make_visualizations(df: pd.DataFrame, username: str, plots_dir: Path, logger):
    plots_dir.mkdir(parents=True, exist_ok=True)
    if df.empty:
        logger.warning("No games available to visualize")
        return

    result_counts = df["result"].value_counts()
    df_sorted = df.sort_values("date")
    color_win = df.groupby("color")["result"].apply(lambda s: (s == "win").mean() * 100)
    mode_counts = df["speed"].value_counts()
    result_colors = {"win": "#4caf50", "loss": "#f44336", "draw": "#9e9e9e"}

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle(f"Lichess Analysis - {username}", fontsize=14)

    axes[0, 0].bar(result_counts.index, result_counts.values, color=[result_colors[r] for r in result_counts.index])
    axes[0, 0].set_title("Results")
    axes[0, 0].set_ylabel("Games")

    axes[0, 1].plot(df_sorted["date"], df_sorted["player_rating"], marker="o", markersize=3, linewidth=1)
    axes[0, 1].set_title("Rating progression")
    axes[0, 1].tick_params(axis="x", rotation=30)

    axes[1, 0].bar(color_win.index, color_win.values, color=["#607d8b", "#263238"])
    axes[1, 0].set_title("Win rate by color (%)")
    axes[1, 0].set_ylim(0, 100)

    axes[1, 1].bar(mode_counts.index, mode_counts.values, color="#3f51b5")
    axes[1, 1].set_title("Games per mode")
    axes[1, 1].tick_params(axis="x", rotation=30)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    dashboard_path = plots_dir / f"dashboard_{username}.png"
    fig.savefig(dashboard_path, dpi=150)
    plt.close(fig)
    logger.info("Saved dashboard to %s", dashboard_path)

    individual_charts = [
        ("results.png", "Results", lambda: plt.bar(result_counts.index, result_counts.values, color=[result_colors[r] for r in result_counts.index])),
        ("rating_progression.png", "Rating progression", lambda: plt.plot(df_sorted["date"], df_sorted["player_rating"], marker="o", markersize=3)),
        ("color_winrate.png", "Win rate by color (%)", lambda: plt.bar(color_win.index, color_win.values, color=["#607d8b", "#263238"])),
        ("mode_distribution.png", "Games per mode", lambda: plt.bar(mode_counts.index, mode_counts.values, color="#3f51b5")),
    ]
    for filename, title, plot_fn in individual_charts:
        plt.figure(figsize=(7, 5))
        plot_fn()
        plt.title(title)
        plt.xticks(rotation=30)
        plt.tight_layout()
        plt.savefig(plots_dir / filename, dpi=150)
        plt.close()

    logger.info("Saved individual charts to %s", plots_dir)


def main():
    load_dotenv()
    args = parse_args()
    logger = setup_logging(LOG_FILE, "game_analysis")

    if args.demo:
        username = DEMO_USERNAME
        logger.info("Running in --demo mode: using local sample data from %s (no live API calls)", DEMO_FIXTURE)
        games = load_demo_games(DEMO_FIXTURE)
    else:
        if not args.username:
            raise SystemExit("A Lichess username is required (--username or LICHESS_USERNAME in .env), or use --demo")
        username = args.username
        logger.info("Fetching up to %s games for '%s'", args.max_games, username)
        client = LichessClient(token=os.getenv("LICHESS_TOKEN"))
        games = client.stream_user_games(username, max_games=args.max_games)

    output_dir = Path(args.output_dir)
    data_dir = output_dir / "data"
    plots_dir = output_dir / "plots"
    data_dir.mkdir(parents=True, exist_ok=True)

    try:
        df = fetch_games_dataframe(games, username, logger)
    except LichessAPIError as exc:
        logger.error("Failed to fetch games: %s", exc)
        raise SystemExit(1)

    games_csv = data_dir / f"games_{username}.csv"
    df.to_csv(games_csv, index=False)
    logger.info("Exported raw games to %s", games_csv)

    stats_df = build_stats(df)
    stats_csv = data_dir / f"stats_summary_{username}.csv"
    stats_df.to_csv(stats_csv, index=False)
    logger.info("Exported stats summary to %s", stats_csv)

    make_visualizations(df, username, plots_dir, logger)
    logger.info("Analysis complete for '%s'", username)


if __name__ == "__main__":
    main()
