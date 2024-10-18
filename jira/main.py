# jira/main.py

import asyncio
from types import SimpleNamespace

import click
from sqlalchemy.orm import joinedload

from database import get_db
from models import Blocker, Comment, Epic, Iteration, Label, Person, Project, Story

from .api import JiraAPI
from .config import Config
from .exceptions import JiraMigrationError
from .jira_setup import JiraSetup
from .logger import logger
from .migrators.comment_migrator import CommentMigrator
from .migrators.issue_migrator import IssueMigrator
from .migrators.project_migrator import ProjectMigrator
from .migrators.sprint_migrator import SprintMigrator
from .migrators.user_migrator import UserMigrator
from .utils import (
    clear_imported_projects,
    get_imported_projects,
    mark_project_as_imported,
    with_progress,
)


class MigrationOrchestrator:
    def __init__(self, jira_api: JiraAPI):
        self.jira_api = jira_api
        self.jira_setup = JiraSetup(self.jira_api)
        self.project_migrator = ProjectMigrator(self.jira_api)
        self.user_migrator = UserMigrator(self.jira_api)
        self.issue_migrator = IssueMigrator(self.jira_api, self.user_migrator)
        self.sprint_migrator = SprintMigrator(self.jira_api)
        self.comment_migrator = CommentMigrator(self.jira_api, self.user_migrator)

    async def run_global_setup(self):
        await self.jira_setup.run_global_setup()

    @with_progress(desc="Migrating Project", total=9)
    async def migrate_project(self, pt_project, force_update=False, pbar=None):
        """
        Migrate a Pivotal Tracker project to Jira.

        :param pt_project: Pivotal Tracker project object from the database
        :param force_update: Whether to force update even if the project was previously imported
        :param pbar: Progress bar object
        :return: JiraProject object or None if skipped
        """
        project_id = pt_project.id
        project_name = pt_project.name

        imported_projects = get_imported_projects()

        if project_id in imported_projects and not force_update:
            logger.info(
                f"Skipping project {project_id} - {project_name} (already imported)"
            )
            if pbar:
                pbar.update(9)
            return None

        logger.info(f"Migrating project: {project_id} - {project_name}")

        try:
            # Migrate project
            jira_project = await self.project_migrator.migrate(pt_project)
            if pbar is not None:
                pbar.update(1)

            # Migrate users
            await self.user_migrator.migrate_users(pt_project.members)
            if pbar is not None:
                pbar.update(1)

            label_mapping = await get_pt_label_mapping(pt_project.id)

            # Migrate epics
            epics = self._prepare_epics(pt_project.epics)
            epic_map = await self.issue_migrator.migrate_epics(jira_project, epics)
            if pbar is not None:
                pbar.update(1)

            # Migrate issues
            stories = self._prepare_stories(pt_project.stories)
            issue_map = await self.issue_migrator.migrate_issues(jira_project, stories)
            if pbar is not None:
                pbar.update(1)

            # Link issues to epics
            await self.issue_migrator.link_issues_to_epics(
                issue_map, epic_map, stories, epics, label_mapping
            )
            if pbar is not None:
                pbar.update(1)

            # Process blockers
            await self.issue_migrator.process_blockers(issue_map, stories)
            if pbar is not None:
                pbar.update(1)

            # Migrate sprints
            iterations = self._prepare_iterations(pt_project.iterations)
            if iterations:
                sprint_map = await self.sprint_migrator.migrate_sprints(
                    jira_project, iterations
                )
                if pbar is not None:
                    pbar.update(1)

                # Associate issues with sprints
                for pt_iteration in pt_project.iterations:
                    sprint_id = sprint_map[pt_iteration.number]
                    iteration_issue_keys = [
                        issue_map[story.id]
                        for story in pt_iteration.stories
                        if story.id in issue_map
                    ]
                    await self.sprint_migrator.associate_issues_with_sprint(
                        sprint_id, iteration_issue_keys
                    )
                if pbar is not None:
                    pbar.update(1)
            else:
                logger.info("No iterations to migrate")
                if pbar is not None:
                    pbar.update(
                        2
                    )  # Update for both sprint migration and issue association steps

            # Migrate comments (including attachments)
            for pt_story in pt_project.stories:
                jira_issue_key = issue_map[pt_story.id]
                comments = self._prepare_comments(pt_story.comments)
                await self.comment_migrator.migrate_comments(jira_issue_key, comments)
            if pbar is not None:
                pbar.update(1)

            mark_project_as_imported(project_id)

            logger.info(
                f"Migration completed successfully for project: {pt_project.name}"
            )
            return jira_project

        except Exception as e:
            logger.error(f"Migration failed for project {pt_project.name}: {str(e)}")
            raise JiraMigrationError(
                f"Migration failed for project {pt_project.name}: {str(e)}"
            )

    def _prepare_epics(self, db_epics):
        prepared_epics = []
        for epic in db_epics:
            prepared_epic = SimpleNamespace(
                id=epic.id,
                name=epic.name,
                description=epic.description,
                created_at=epic.created_at,
                updated_at=epic.updated_at,
                label_id=epic.label_id,
            )
            prepared_epics.append(prepared_epic)
        return prepared_epics

    def _prepare_stories(self, db_stories):
        prepared_stories = []
        for story in db_stories:
            prepared_story = SimpleNamespace(
                id=story.id,
                name=story.name,
                description=story.description,
                story_type=story.story_type,
                current_state=story.current_state,
                estimate=story.estimate,
                accepted_at=story.accepted_at,
                created_at=story.created_at,
                updated_at=story.updated_at,
                requested_by_id=story.requested_by_id,
                owner_ids=[owner.id for owner in story.owners],
                labels=[label.name for label in story.labels],
                blockers=[blocker for blocker in story.blockers],
                tasks=[task for task in story.tasks],
            )
            prepared_stories.append(prepared_story)
        return prepared_stories

    def _prepare_iterations(self, db_iterations):
        prepared_iterations = []
        for iteration in db_iterations:
            prepared_iteration = SimpleNamespace(
                number=iteration.number,
                start=iteration.start,
                finish=iteration.finish,
                stories=self._prepare_stories(iteration.stories),
            )
            prepared_iterations.append(prepared_iteration)
        return prepared_iterations

    def _prepare_comments(self, db_comments):
        prepared_comments = []
        for comment in db_comments:
            prepared_comment = SimpleNamespace(
                id=comment.id,
                text=comment.text,
                person_id=comment.person_id,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                attachments=comment.file_attachments,
            )
            prepared_comments.append(prepared_comment)
        return prepared_comments


async def get_pt_projects(project_ids=None):
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

        # Detach the objects from the session
        db.expunge_all()

        return projects


async def get_pt_label_mapping(project_id):
    with get_db() as db:
        query = db.query(Label).filter(Label.project_id == project_id)
        labels = query.all()

        # turn the labels into a map of {name: id}
        label_mapping = {label.name: label.id for label in labels}

        db.expunge_all()
        return label_mapping


@click.command()
@click.option(
    "--project-ids",
    "-p",
    multiple=True,
    type=int,
    help="Specific project IDs to migrate",
)
@click.option(
    "--all", "migrate_all", is_flag=True, help="Migrate all projects in the database"
)
@click.option(
    "--force", is_flag=True, help="Force update even for already imported projects"
)
@click.option(
    "--clear",
    is_flag=True,
    help="Clear the imported projects list before running the migration",
)
def main(project_ids, migrate_all, force, clear):
    if clear:
        click.echo("Clearing the imported projects list...")
        clear_imported_projects()
        click.echo("Imported projects list cleared.")

    if not project_ids and not migrate_all:
        click.echo("Please specify either project IDs or use the --all flag.")
        return

    asyncio.run(run_migration(project_ids, migrate_all, force))


@with_progress(desc="Migrating Projects")
async def run_migration(project_ids, migrate_all, force_update=False, pbar=None):
    jira_api = JiraAPI()
    try:
        orchestrator = MigrationOrchestrator(jira_api)

        # Run global setup once
        await orchestrator.run_global_setup()

        # Get projects to migrate
        if migrate_all:
            pt_projects = await get_pt_projects()
        else:
            pt_projects = await get_pt_projects(project_ids)

        # Set the total for the progress bar
        if pbar is not None:
            pbar.total = len(pt_projects)
            pbar.refresh()

        with get_db() as db:
            for pt_project in pt_projects:
                # Reattach the project to the session
                db.add(pt_project)
                try:
                    jira_project = await orchestrator.migrate_project(
                        pt_project, force_update
                    )
                    if jira_project:
                        click.echo(
                            f"Migration completed for project: {pt_project.name}. New Jira project key: {jira_project.key}"
                        )
                except JiraMigrationError as e:
                    click.echo(
                        f"Migration failed for project {pt_project.name}: {str(e)}"
                    )
                finally:
                    # Clear the session to prevent memory buildup
                    db.expunge_all()
                    if pbar is not None:
                        pbar.update(1)
    finally:
        await jira_api.close()


if __name__ == "__main__":
    main()
