# jira/migrators/sprint_migrator.py

from datetime import datetime

from ..api import JiraAPI
from ..exceptions import SprintMigrationError
from ..logger import logger
from ..models import JiraSprint
from ..utils import with_progress


class SprintMigrator:
    def __init__(self, jira_api: JiraAPI):
        self.jira_api = jira_api

    @with_progress(desc="Migrating Sprints")
    async def migrate_sprints(self, jira_project, pt_iterations, pbar=None):
        """
        Migrate Pivotal Tracker iterations to Jira sprints.

        :param jira_project: JiraProject object
        :param pt_iterations: List of Pivotal Tracker iteration objects
        :param pbar: Progress bar object
        :return: Dictionary mapping PT iteration numbers to Jira sprint IDs
        """
        logger.info(f"Starting migration for {len(pt_iterations)} iterations")
        if pbar is not None:
            pbar.total = len(pt_iterations)
            pbar.refresh()

        sprint_map = {}

        for pt_iteration in pt_iterations:
            try:
                jira_sprint = await self.migrate_sprint(jira_project, pt_iteration)
                sprint_map[pt_iteration.number] = jira_sprint.id
                if pbar is not None:
                    pbar.update(1)
            except SprintMigrationError as e:
                logger.warning(
                    f"Failed to migrate iteration {pt_iteration.number}: {str(e)}"
                )
                # Continue with the next iteration

        logger.info(f"Sprint migration completed. Migrated {len(sprint_map)} sprints")
        return sprint_map

    async def migrate_sprint(self, jira_project, pt_iteration):
        """
        Migrate a single Pivotal Tracker iteration to a Jira sprint.

        :param jira_project: JiraProject object
        :param pt_iteration: Pivotal Tracker iteration object
        :return: JiraSprint object
        """
        logger.info(f"Migrating iteration: {pt_iteration.number}")

        try:
            sprint_name = f"Sprint {pt_iteration.number}"
            start_date = pt_iteration.start.isoformat() if pt_iteration.start else None
            end_date = pt_iteration.finish.isoformat() if pt_iteration.finish else None

            # Get the board ID for the Jira project
            board_id = jira_project.board_id

            sprint_data = {
                "name": sprint_name,
                "startDate": start_date,
                "endDate": end_date,
                "originBoardId": board_id,
                "goal": f"Iteration {pt_iteration.number} from Pivotal Tracker",
            }

            created_sprint = await self.jira_api.create_sprint(sprint_data)

            return JiraSprint(
                id=created_sprint["id"],
                name=created_sprint["name"],
                start_date=datetime.fromisoformat(start_date) if start_date else None,
                end_date=datetime.fromisoformat(end_date) if end_date else None,
                board_id=board_id,
            )

        except Exception as e:
            raise SprintMigrationError(
                f"Failed to migrate iteration {pt_iteration.number}: {str(e)}"
            )

    @with_progress(desc="Associating Issues with Sprints")
    async def associate_issues_with_sprint(self, sprint_id, issue_keys, pbar=None):
        """
        Associate Jira issues with a sprint.

        :param sprint_id: ID of the Jira sprint
        :param issue_keys: List of Jira issue keys to associate with the sprint
        :param pbar: Progress bar object
        """
        try:
            if pbar is not None:
                pbar.total = len(issue_keys)
                pbar.refresh()

            # Process issues in batches of 45
            for i in range(0, len(issue_keys), 45):
                issue_key_batch = issue_keys[i : i + 45]
                await self.jira_api.add_issues_to_sprint(sprint_id, issue_key_batch)
                logger.info(
                    f"Associated {len(issue_key_batch)} issues with sprint {sprint_id}"
                )
                if pbar is not None:
                    pbar.update(len(issue_key_batch))

            logger.info(
                f"Associated all {len(issue_keys)} issues with sprint {sprint_id}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to associate issues with sprint {sprint_id}: {str(e)}"
            )
