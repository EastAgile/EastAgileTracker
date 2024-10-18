# main.py

import asyncio

from cli import cli
from database import init_db


def main():
    # Initialize the database
    init_db()

    # Run the CLI
    cli()


if __name__ == "__main__":
    main()
