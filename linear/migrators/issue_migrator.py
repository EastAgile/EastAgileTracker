# linear/migrators/issue_migrator.py

from database import get_db

from ..api import LinearAPI
from ..config import Config
from ..exceptions import IssueMigrationError
from ..logger import logger
from ..models import LinearIssue, LinearWorkflowState
from ..utils import (
    map_issue_type,
    map_priority,
    map_state,
    sanitize_name,
    with_progress,
)


class IssueMigrator:
    def __init__(
        self,
        linear_api: LinearAPI,
        user_migrator,
        team_migrator,
        project_migrator,
        cycle_migrator,
    ):
        self.linear_api = linear_api
        self.user_migrator = user_migrator
        self.team_migrator = team_migrator
        self.project_migrator = project_migrator
        self.cycle_migrator = cycle_migrator
        self.issue_map = {}  # Map PT story IDs to Linear issue objects
        self.workflow_states = {}  # Cache for workflow states
        self.label_epic_map = {}  # Map label IDs to epic IDs

    @with_progress(desc="Migrating Issues")
    async def migrate_issues(
        self, pt_stories, linear_team_id, pt_project_id, pbar=None
    ):
        """
        Migrate a list of Pivotal Tracker stories to Linear issues.

        :param pt_stories: List of Pivotal Tracker story objects from the database
        :param linear_team_id: ID of the Linear team to create issues in
        :param pbar: Progress bar object
        :return: Dictionary mapping PT story IDs to Linear issue objects
        """
        logger.info(f"Starting migration for {len(pt_stories)} stories to issues")
        if pbar:
            pbar.total = len(pt_stories)
            pbar.refresh()

        self.label_epic_map = await get_label_epic_map(pt_project_id)

        # Fetch and cache workflow states
        await self.fetch_workflow_states(linear_team_id)

        for pt_story in pt_stories:
            try:
                linear_issue = await self.migrate_issue(pt_story, linear_team_id)
                self.issue_map[pt_story.id] = linear_issue
                if pbar:
                    pbar.update(1)
            except IssueMigrationError as e:
                logger.warning(f"Failed to migrate story {pt_story.id}: {str(e)}")
                # Continue with the next story

        logger.info(f"Issue migration completed. Migrated {len(self.issue_map)} issues")
        return self.issue_map

    async def fetch_workflow_states(self, linear_team_id):
        """Fetch and cache workflow states for the team."""
        states = await self.linear_api.get_workflow_states(linear_team_id)
        self.workflow_states = {state["name"]: state["id"] for state in states}

    async def migrate_issue(self, pt_story, linear_team_id):
        """
        Migrate a single Pivotal Tracker story to a Linear issue.

        :param pt_story: Pivotal Tracker story object from the database
        :param linear_team_id: ID of the Linear team to create the issue in
        :return: LinearIssue object
        """
        logger.info(f"Migrating story to issue: {pt_story.id}")

        try:
            # Map Pivotal Tracker attributes to Linear attributes
            title = sanitize_name(pt_story.name)
            description = pt_story.description or ""
            state_id = self.workflow_states.get(map_state(pt_story.current_state))
            priority = map_priority(pt_story.story_priority)
            estimate = pt_story.estimate
            labels = [label.name for label in pt_story.labels]

            # Get assignee and creator
            assignee_id = None
            if pt_story.owner_ids:
                linear_user = self.user_migrator.get_linear_user(pt_story.owner_ids[0])
                if linear_user:
                    assignee_id = linear_user.id

            creator_id = None
            if pt_story.requested_by_id:
                linear_user = self.user_migrator.get_linear_user(
                    pt_story.requested_by_id
                )
                if linear_user:
                    creator_id = linear_user.id

            # Get project (epic) if applicable
            project_id = None
            if pt_story.label_ids:
                for label_id in pt_story.label_ids:
                    pt_epic_id = self.label_epic_map.get(label_id)
                    linear_project = self.project_migrator.get_linear_project(
                        pt_epic_id
                    )
                    if linear_project:
                        project_id = linear_project.id
                        break

            # Get cycle if applicable
            cycle_id = None
            if pt_story.iteration:
                linear_cycle = self.cycle_migrator.get_linear_cycle(
                    pt_story.iteration.number
                )
                if linear_cycle:
                    cycle_id = linear_cycle.id

            # Create the issue in Linear
            linear_issue_data = await self.linear_api.create_issue(
                team_id=linear_team_id,
                title=title,
                description=description,
                state_id=state_id,
                priority=priority,
                estimate=estimate,
                assignee_id=assignee_id,
                creator_id=creator_id,
                project_id=project_id,
                cycle_id=cycle_id,
                labels=labels,
            )

            # Create LinearIssue object
            linear_issue = LinearIssue(
                id=linear_issue_data["id"],
                title=linear_issue_data["title"],
                description=linear_issue_data["description"],
                team_id=linear_team_id,
                project_id=project_id,
                cycle_id=cycle_id,
                assignee_id=assignee_id,
                creator_id=creator_id,
                state_id=state_id,
                priority=priority,
                estimate=estimate,
                labels=labels,
                created_at=pt_story.created_at,
                updated_at=pt_story.updated_at,
            )

            # Migrate tasks as sub-issues
            if pt_story.tasks:
                await self.migrate_tasks(pt_story.tasks, linear_issue, linear_team_id)

            return linear_issue

        except Exception as e:
            raise IssueMigrationError(
                f"Failed to migrate story {pt_story.id}: {str(e)}"
            )

    async def migrate_tasks(self, pt_tasks, parent_issue, linear_team_id):
        """
        Migrate Pivotal Tracker tasks as sub-issues in Linear.

        :param pt_tasks: List of Pivotal Tracker task objects
        :param parent_issue: Parent LinearIssue object
        :param linear_team_id: ID of the Linear team
        """
        for pt_task in pt_tasks:
            try:
                sub_issue_data = await self.linear_api.create_issue(
                    team_id=linear_team_id,
                    title=sanitize_name(pt_task.description),
                    description="",
                    state_id=self.workflow_states.get("Todo"),
                    parent_id=parent_issue.id,
                )

                sub_issue = LinearIssue(
                    id=sub_issue_data["id"],
                    title=sub_issue_data["title"],
                    description=sub_issue_data["description"],
                    team_id=linear_team_id,
                    parent_id=parent_issue.id,
                    state_id=self.workflow_states.get("Todo"),
                    created_at=pt_task.created_at,
                    updated_at=pt_task.updated_at,
                )

                parent_issue.sub_issues.append(sub_issue)

                # If the task is complete, update its state
                if pt_task.complete:
                    await self.linear_api.update_issue(
                        sub_issue.id, {"stateId": self.workflow_states.get("Done")}
                    )

            except Exception as e:
                logger.warning(f"Failed to migrate task {pt_task.id}: {str(e)}")

    def get_linear_issue(self, pt_story_id):
        """
        Get the Linear issue object for a given Pivotal Tracker story ID.

        :param pt_story_id: Pivotal Tracker story ID
        :return: LinearIssue object or None if not found
        """
        return self.issue_map.get(pt_story_id)

    async def ensure_issue(self, pt_story, linear_team_id):
        """
        Ensure an issue exists in Linear, migrating if necessary.

        :param pt_story: Pivotal Tracker story object
        :param linear_team_id: ID of the Linear team to create the issue in
        :return: LinearIssue object
        """
        if pt_story.id not in self.issue_map:
            linear_issue = await self.migrate_issue(pt_story, linear_team_id)
            self.issue_map[pt_story.id] = linear_issue
        return self.issue_map[pt_story.id]

    async def get_label_epic_map(project_id: int):
        """Retrieve a mapping of label IDs to epic IDs for a given project."""
        with get_db() as db:
            label_epic_map = {
                epic.label_id: epic.id
                for epic in db.query(Epic).filter_by(project_id=project_id).all()
            }
            db.expunge_all()
            return label_epic_map
