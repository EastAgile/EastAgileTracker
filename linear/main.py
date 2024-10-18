# linear/main.py

import asyncio
from typing import List, Optional

import click
from sqlalchemy.orm import joinedload
from tqdm import tqdm

from database import get_db, init_db
from models import Comment, Epic, Iteration, Label, Person, Project, Story

from .api import LinearAPI
from .config import Config
from .exceptions import LinearMigrationError
from .linear_setup import LinearSetup
from .logger import logger
from .migrators.comment_migrator import CommentMigrator
from .migrators.cycle_migrator import CycleMigrator
from .migrators.issue_migrator import IssueMigrator
from .migrators.project_migrator import ProjectMigrator
from .migrators.relation_migrator import RelationMigrator
from .migrators.team_migrator import TeamMigrator
from .migrators.user_migrator import UserMigrator
from .utils import (
    clear_processed_teams,
    get_processed_teams,
    mark_team_as_processed,
    with_progress,
)


class MigrationOrchestrator:
    def __init__(self, linear_api: LinearAPI):
        self.linear_api = linear_api
        self.linear_setup = LinearSetup(self.linear_api)
        self.user_migrator = UserMigrator(self.linear_api)
        self.team_migrator = TeamMigrator(self.linear_api, self.linear_setup)
        self.project_migrator = ProjectMigrator(self.linear_api)
        self.cycle_migrator = CycleMigrator(self.linear_api)
        self.issue_migrator = IssueMigrator(
            self.linear_api,
            self.user_migrator,
            self.team_migrator,
            self.project_migrator,
            self.cycle_migrator,
        )
        self.comment_migrator = CommentMigrator(self.linear_api, self.user_migrator)
        self.relation_migrator = RelationMigrator(self.linear_api, self.issue_migrator)

    async def run_global_setup(self):
        await self.linear_setup.run_global_setup()

    @with_progress(desc="Migrating Project")
    async def migrate_project(
        self,
        pt_project: Project,
        force_update: bool = False,
        pbar: Optional[tqdm] = None,
    ):
        """
        Migrate a Pivotal Tracker project to Linear.

        :param pt_project: Pivotal Tracker project object from the database
        :param force_update: Whether to force update even if the project was previously migrated
        :param pbar: Progress bar object
        :return: LinearTeam object or None if skipped
        """
        project_id = pt_project.id
        project_name = pt_project.name

        processed_teams = get_processed_teams()

        if project_id in processed_teams and not force_update:
            logger.info(
                f"Skipping project {project_id} - {project_name} (already migrated)"
            )
            if pbar:
                pbar.update(7)
            return None

        logger.info(f"Migrating project: {project_id} - {project_name}")

        try:
            # Migrate team (project)
            linear_team = await self.team_migrator.migrate_team(pt_project)
            if pbar:
                pbar.update(1)

            # Migrate users
            Config.LINEAR_USER_MAP = await self.user_migrator.migrate_users(
                pt_project.members, linear_team.id
            )
            if pbar:
                pbar.update(1)

            # Migrate epics as projects
            await self.project_migrator.migrate_projects(
                pt_project.epics, linear_team.id
            )
            if pbar:
                pbar.update(1)

            # Migrate iterations as cycles
            await self.cycle_migrator.migrate_cycles(
                pt_project.iterations, linear_team.id, pt_project
            )
            if pbar:
                pbar.update(1)

            # Migrate stories as issues
            await self.issue_migrator.migrate_issues(
                pt_project.stories, linear_team.id, pt_project.id
            )
            if pbar:
                pbar.update(1)

            # Migrate comments and attachments
            for pt_story in pt_project.stories:
                linear_issue = self.issue_migrator.get_linear_issue(pt_story.id)
                if linear_issue:
                    await self.comment_migrator.migrate_comments(
                        pt_story.comments, linear_issue.id
                    )
            if pbar:
                pbar.update(1)

            # Migrate relations (blockers)
            await self.relation_migrator.migrate_relations(pt_project.stories)
            if pbar:
                pbar.update(1)

            # Additional steps can be added here if needed

            mark_team_as_processed(project_id)
            logger.info(f"Successfully migrated project {project_id} - {project_name}")
            return linear_team

        except Exception as e:
            logger.error(f"Error migrating project {project_id}: {str(e)}")
            raise LinearMigrationError(
                f"Migration failed for project {project_name}: {str(e)}"
            )


async def get_pt_projects(project_ids: Optional[List[int]] = None):
    """
    Retrieve Pivotal Tracker projects from the database.

    :param project_ids: Optional list of project IDs to retrieve
    :return: List of Project objects with related data
    """
    with get_db() as db:
        query = db.query(Project).options(
            joinedload(Project.members),
            joinedload(Project.stories).joinedload(Story.labels),
            joinedload(Project.stories)
            .joinedload(Story.comments)
            .joinedload(Comment.file_attachments),
            joinedload(Project.stories).joinedload(Story.owners),
            joinedload(Project.stories).joinedload(Story.blockers),
            joinedload(Project.iterations),
            joinedload(Project.epics),
        )

        if project_ids:
            query = query.filter(Project.id.in_(project_ids))

        projects = query.all()
        db.expunge_all()
        return projects


async def run_migration(
    project_ids: Optional[List[int]] = None,
    migrate_all: bool = False,
    force_update: bool = False,
):
    async with LinearAPI() as linear_api:
        try:
            orchestrator = MigrationOrchestrator(linear_api)

            # Run global setup once
            await orchestrator.run_global_setup()

            # Get projects to migrate
            if migrate_all:
                pt_projects = await get_pt_projects()
            else:
                pt_projects = await get_pt_projects(project_ids)

            for pt_project in tqdm(pt_projects, desc="Migrating Projects"):
                try:
                    linear_team = await orchestrator.migrate_project(
                        pt_project, force_update
                    )
                    if linear_team:
                        logger.info(
                            f"Migration completed for project: {pt_project.name}. New Linear team key: {linear_team.key}"
                        )
                except LinearMigrationError as e:
                    logger.error(
                        f"Migration failed for project {pt_project.name}: {str(e)}"
                    )

        except Exception as e:
            logger.error(f"An error occurred during migration: {str(e)}")


@click.command()
@click.option(
    "-p",
    "--project-ids",
    multiple=True,
    type=int,
    help="Specific project IDs to migrate. If not provided, all projects in the database will be migrated.",
)
@click.option(
    "--all",
    "migrate_all",
    is_flag=True,
    help="Migrate all projects in the database",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force update even for already migrated projects.",
)
@click.option(
    "--clear",
    is_flag=True,
    help="Clear the migrated projects list before running the migration",
)
def main(project_ids, migrate_all, force, clear):
    if clear:
        click.echo("Clearing the migrated projects list...")
        clear_processed_teams()
        click.echo("Migrated projects list cleared.")

    if not project_ids and not migrate_all:
        click.echo("Please specify either project IDs or use the --all flag.")
        return

    init_db()  # Ensure the database schema is up to date

    asyncio.run(run_migration(project_ids, migrate_all, force))


if __name__ == "__main__":
    main()
