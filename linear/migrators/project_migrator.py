# linear/migrators/project_migrator.py

from ..api import LinearAPI
from ..exceptions import ProjectCreationError
from ..logger import logger
from ..models import LinearProject
from ..utils import sanitize_name, with_progress


class ProjectMigrator:
    def __init__(self, linear_api: LinearAPI):
        self.linear_api = linear_api
        self.project_map = {}  # Map PT epic IDs to Linear project objects

    @with_progress(desc="Migrating Epics to Projects")
    async def migrate_projects(self, pt_epics, linear_team_id, pbar=None):
        """
        Migrate a list of Pivotal Tracker epics to Linear projects.

        :param pt_epics: List of Pivotal Tracker epic objects from the database
        :param linear_team_id: ID of the Linear team to create projects in
        :param pbar: Progress bar object
        :return: Dictionary mapping PT epic IDs to Linear project objects
        """
        logger.info(f"Starting migration for {len(pt_epics)} epics to projects")
        if pbar:
            pbar.total = len(pt_epics)
            pbar.refresh()

        for pt_epic in pt_epics:
            try:
                linear_project = await self.migrate_project(pt_epic, linear_team_id)
                self.project_map[pt_epic.id] = linear_project
                if pbar:
                    pbar.update(1)
            except ProjectCreationError as e:
                logger.warning(f"Failed to migrate epic {pt_epic.name}: {str(e)}")
                # Continue with the next epic

        logger.info(
            f"Project migration completed. Migrated {len(self.project_map)} projects"
        )
        return self.project_map

    async def migrate_project(self, pt_epic, linear_team_id):
        """
        Migrate a single Pivotal Tracker epic to a Linear project.

        :param pt_epic: Pivotal Tracker epic object from the database
        :param linear_team_id: ID of the Linear team to create the project in
        :return: LinearProject object
        """
        logger.info(f"Migrating epic to project: {pt_epic.name}")

        try:
            # Sanitize the epic name
            sanitized_name = sanitize_name(pt_epic.name)

            # Create the project in Linear
            linear_project_data = await self.linear_api.create_project(
                team_id=linear_team_id,
                name=sanitized_name,
                description=pt_epic.description,
            )

            # Create LinearProject object
            linear_project = LinearProject(
                id=linear_project_data["id"],
                name=linear_project_data["name"],
                description=linear_project_data.get("description"),
                team_id=linear_team_id,
            )

            return linear_project

        except Exception as e:
            raise ProjectCreationError(
                f"Failed to migrate epic {pt_epic.name}: {str(e)}"
            )

    def get_linear_project(self, pt_epic_id):
        """
        Get the Linear project object for a given Pivotal Tracker epic ID.

        :param pt_epic_id: Pivotal Tracker epic ID
        :return: LinearProject object or None if not found
        """
        return self.project_map.get(pt_epic_id)

    async def ensure_project(self, pt_epic, linear_team_id):
        """
        Ensure a project exists in Linear, migrating if necessary.

        :param pt_epic: Pivotal Tracker epic object
        :param linear_team_id: ID of the Linear team to create the project in
        :return: LinearProject object
        """
        if pt_epic.id not in self.project_map:
            linear_project = await self.migrate_project(pt_epic, linear_team_id)
            self.project_map[pt_epic.id] = linear_project
        return self.project_map[pt_epic.id]
