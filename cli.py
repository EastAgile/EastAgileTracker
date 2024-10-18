# cli.py

import asyncio

import click

from api import PivotalTrackerAPI
from config import Config
from database import clear_db, init_db
from etl import extract_and_load_all_projects, extract_and_load_project
from utils import clear_processed_projects, get_processed_projects


@click.group()
def cli():
    """Pivotal Tracker Data Exporter"""
    pass


@cli.command()
@click.option(
    "-p",
    "--project-ids",
    multiple=True,
    help="Specific project IDs to process. If not provided, all accessible projects will be processed.",
)
@click.option(
    "--clear",
    is_flag=True,
    help="Clear the database and processed projects list before running the ETL process.",
)
@click.option(
    "--force", is_flag=True, help="Force update even for already processed projects."
)
def run(project_ids, clear, force):
    """Run the ETL process for Pivotal Tracker data."""
    if clear:
        click.echo("Clearing the database...")
        clear_db()
        clear_processed_projects()
        click.echo("Database and processed projects list cleared.")

    init_db()  # Ensure the database schema is up to date

    if project_ids:
        click.echo(f"Processing specified projects: {', '.join(project_ids)}")
        asyncio.run(process_specific_projects(project_ids, force))
    else:
        click.echo("Processing all accessible projects")
        asyncio.run(extract_and_load_all_projects(force))


async def process_specific_projects(project_ids, force):
    processed_projects = get_processed_projects()
    async with PivotalTrackerAPI() as api:
        for project_id in project_ids:
            if not force and int(project_id) in processed_projects:
                click.echo(f"Skipping project {project_id} (already processed)")
                continue
            try:
                project_data = await api.get_project(project_id)
                await extract_and_load_project(project_data, force)
            except Exception as e:
                click.echo(f"Error processing project {project_id}: {str(e)}")


@cli.command()
def clear():
    """Clear all data from the database and the processed projects list."""
    click.echo("Clearing the database and processed projects list...")
    clear_db()
    clear_processed_projects()
    click.echo("Database and processed projects list cleared.")


@cli.command()
@click.option(
    "--token",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Your Pivotal Tracker API token.",
)
def configure(token):
    """Configure the Pivotal Tracker API token."""
    Config.set_api_token(token)
    click.echo("API token configured successfully.")


if __name__ == "__main__":
    cli()
