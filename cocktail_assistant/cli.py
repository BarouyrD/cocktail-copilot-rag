"""Cross-platform task runner for the Cocktail Copilot RAG project.

Replaces the Unix-only Makefile so the same commands work in PowerShell, bash,
and zsh:

    uv run cocktail-cli download     # fetch the ONNX embedding model
    uv run cocktail-cli ingest       # fetch cocktail data into data/cocktails.csv
    uv run cocktail-cli db           # create the PostgreSQL tables
    uv run cocktail-cli up           # start the full stack (docker compose)
    uv run cocktail-cli down         # stop the stack
    uv run cocktail-cli dashboard    # run the Streamlit monitoring dashboard
    uv run cocktail-cli data         # pump synthetic conversations into the DB
    uv run cocktail-cli app          # run the Streamlit app locally
    uv run cocktail-cli airflow-up   # start the Airflow ingestion stack
    uv run cocktail-cli airflow-down # stop the Airflow ingestion stack

Paths are resolved relative to the project root, so the commands work no matter
which directory you run them from.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "cocktail_assistant"
AIRFLOW_COMPOSE = ROOT / "airflow" / "docker-compose.airflow.yaml"
PY = sys.executable

COMMANDS = {
    "download": [PY, str(PKG / "download.py")],
    "ingest": [PY, str(PKG / "ingest.py")],
    "db": [PY, str(PKG / "db_init.py")],
    "data": [PY, str(PKG / "generate_data.py")],
    "app": [PY, "-m", "streamlit", "run", str(PKG / "app.py")],
    "dashboard": [PY, "-m", "streamlit", "run", str(PKG / "dashboard.py")],
    "up": ["docker", "compose", "up", "--build"],
    "down": ["docker", "compose", "down"],
    "airflow-up": ["docker", "compose", "-f", str(AIRFLOW_COMPOSE), "up"],
    "airflow-down": ["docker", "compose", "-f", str(AIRFLOW_COMPOSE), "down"],
}

HELP = {
    "download": "download the ONNX embedding model into models/",
    "ingest": "fetch cocktail data from TheCocktailDB into data/cocktails.csv",
    "db": "create the PostgreSQL tables",
    "data": "pump synthetic conversations into the database",
    "app": "run the Streamlit app locally",
    "dashboard": "run the Streamlit monitoring dashboard locally",
    "up": "start the full stack (postgres + grafana + streamlit)",
    "down": "stop the full stack",
    "airflow-up": "start the standalone Airflow ingestion stack",
    "airflow-down": "stop the standalone Airflow ingestion stack",
}


def main():
    parser = argparse.ArgumentParser(
        prog="cocktail-cli",
        description="Cross-platform task runner for the Cocktail Copilot RAG project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")
    for name in COMMANDS:
        subparsers.add_parser(name, help=HELP[name])

    args, extra = parser.parse_known_args()

    if not args.command:
        parser.print_help()
        return 1

    cmd = COMMANDS[args.command] + extra
    try:
        return subprocess.call(cmd, cwd=str(ROOT))
    except FileNotFoundError:
        print(
            f"error: '{cmd[0]}' was not found. Make sure it is installed and on your PATH.",
            file=sys.stderr,
        )
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
