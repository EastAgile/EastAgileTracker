# jira/migrators/project_migrator.py

from ..api import JiraAPI
from ..config import Config
from ..exceptions import ProjectCreationError
from ..logger import logger
from ..models import JiraProject
from ..utils import with_progress


class ProjectMigrator:
    def __init__(self, jira_api: JiraAPI):
        self.jira_api = jira_api

    @with_progress(desc="Migrating Project", total=4)
    async def migrate(self, pt_project, pbar=None):
        """
        Migrate a Pivotal Tracker project to Jira.

        :param pt_project: Pivotal Tracker project object from the database
        :param pbar: Progress bar object
        :return: JiraProject object
        """
        logger.info(f"Starting migration for project: {pt_project.name}")

        # Create Jira project
        try:
            jira_project_data = await self.jira_api.create_project(
                key=self._generate_project_key(pt_project.name),
                name=pt_project.name,
                description=pt_project.description or "",
            )

            # Associate the project with the global workflow scheme
            scheme_id = Config.GLOBAL_WORKFLOW_SCHEME_ID
            await self.jira_api.assign_workflow_scheme_to_project(
                jira_project_data["id"], scheme_id
            )

            logger.info(f"Jira project created: {jira_project_data['key']}")
        except Exception as e:
            logger.error(f"Failed to create Jira project: {str(e)}")
            raise ProjectCreationError(f"Failed to create Jira project: {str(e)}")

        # Create JiraProject object
        jira_project = JiraProject(
            key=jira_project_data["key"],
            name=pt_project.name,
            description=pt_project.description or "",
            url=jira_project_data.get("self"),
        )

        if pbar:
            pbar.update(1)

        logger.info(f"Creating Agile board for project: {pt_project.name}")

        # Create an Agile board for the project
        try:
            filter = await self.jira_api.create_filter_for_project(jira_project.key)
            board_data = await self.jira_api.create_board(
                jira_project.key, filter["id"]
            )
            jira_project.board_id = board_data["id"]
            logger.info(f"Created Agile board for project: {jira_project.key}")
            if pbar:
                pbar.update(1)
        except Exception as e:
            logger.error(f"Failed to create Agile board: {str(e)}")
            # You might want to handle this error differently, e.g., continue without a board
            # raise ProjectCreationError(f"Failed to create Agile board: {str(e)}")

        logger.info(f"Configuring custom fields for project: {pt_project.name}")
        # Get the default create and edit issue screens
        screen_ids = await self.jira_api.get_issue_screen_ids(jira_project.key)

        for screen_id in screen_ids:
            # Get the tab of that screen
            tab_id = await self.jira_api.get_screen_tab_id(screen_id)

            # Add the custom field to the tab
            for field in Config.JIRA_CUSTOM_FIELDS:
                try:
                    await self.jira_api.add_custom_field_to_screen_tab(
                        screen_id, tab_id, field
                    )
                except Exception as e:
                    logger.warning(f"Failed to add custom field to screen: {str(e)}")

        if pbar:
            pbar.update(1)

        logger.info(f"Adding administrator role for project: {pt_project.name}")

        # Add the user to the project's administrator role so we can set reporter field
        admin_role = await self.jira_api.get_project_role_id(
            jira_project.key, "Administrators"
        )
        if not admin_role:
            logger.error("Failed to get project role ID for Administrators")
            raise ProjectCreationError(
                "Failed to get project role ID for Administrators"
            )

        await self.jira_api.add_user_to_project_role(
            jira_project.key, admin_role, Config.JIRA_ACCOUNT_ID
        )

        if pbar:
            pbar.update(1)
        logger.info(f"Project migration completed: {jira_project.key}")

        return jira_project

    def _generate_project_key(self, project_name):
        """
        Generate a valid Jira project key from the project name.

        :param project_name: Name of the project
        :return: A valid Jira project key
        """
        # Remove non-alphanumeric characters and convert to uppercase
        key = "".join(char.upper() for char in project_name if char.isalnum())

        # Jira project keys must start with a letter
        if not key[0].isalpha():
            key = "P" + key

        # Jira project keys must be between 2 and 10 characters
        return key[:10] if len(key) > 10 else key.ljust(2, "X")
