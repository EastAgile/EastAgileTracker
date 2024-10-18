# linear/migrators/cycle_migrator.py

from ..api import LinearAPI
from ..exceptions import CycleMigrationError
from ..logger import logger
from ..models import LinearCycle
from ..utils import with_progress


class CycleMigrator:
    def __init__(self, linear_api: LinearAPI):
        self.linear_api = linear_api
        self.pt_project = None
        self.cycle_map = {}  # Map PT iteration numbers to Linear cycle objects

    @with_progress(desc="Migrating Iterations to Cycles")
    async def migrate_cycles(
        self, pt_iterations, linear_team_id, pt_project, pbar=None
    ):
        """
        Migrate a list of Pivotal Tracker iterations to Linear cycles.

        :param pt_iterations: List of Pivotal Tracker iteration objects from the database
        :param linear_team_id: ID of the Linear team to create cycles in
        :param pbar: Progress bar object
        :return: Dictionary mapping PT iteration numbers to Linear cycle objects
        """
        logger.info(f"Starting migration for {len(pt_iterations)} iterations to cycles")
        if pbar:
            pbar.total = len(pt_iterations)
            pbar.refresh()

        self.pt_project = pt_project

        for pt_iteration in pt_iterations:
            try:
                linear_cycle = await self.migrate_cycle(pt_iteration, linear_team_id)
                self.cycle_map[pt_iteration.number] = linear_cycle
                if pbar:
                    pbar.update(1)
            except CycleMigrationError as e:
                logger.warning(
                    f"Failed to migrate iteration {pt_iteration.number}: {str(e)}"
                )
                # Continue with the next iteration

        logger.info(f"Cycle migration completed. Migrated {len(self.cycle_map)} cycles")
        return self.cycle_map

    async def migrate_cycle(self, pt_iteration, linear_team_id):
        """
        Migrate a single Pivotal Tracker iteration to a Linear cycle.

        :param pt_iteration: Pivotal Tracker iteration object from the database
        :param linear_team_id: ID of the Linear team to create the cycle in
        :return: LinearCycle object
        """
        logger.info(f"Migrating iteration to cycle: {pt_iteration.number}")

        try:
            # Create the cycle in Linear
            linear_cycle_data = await self.linear_api.create_cycle(
                team_id=linear_team_id,
                name=f"{self.pt_project.name} - Iteration {pt_iteration.number}",
                start_date=pt_iteration.start.isoformat(),
                end_date=pt_iteration.finish.isoformat(),
            )

            # Create LinearCycle object
            linear_cycle = LinearCycle(
                id=linear_cycle_data["id"],
                number=linear_cycle_data["number"],
                name=linear_cycle_data["name"],
                start_date=linear_cycle_data["startDate"],
                end_date=linear_cycle_data["endDate"],
                team_id=linear_team_id,
            )

            return linear_cycle

        except Exception as e:
            raise CycleMigrationError(
                f"Failed to migrate iteration {pt_iteration.number}: {str(e)}"
            )

    def get_linear_cycle(self, pt_iteration_number):
        """
        Get the Linear cycle object for a given Pivotal Tracker iteration number.

        :param pt_iteration_number: Pivotal Tracker iteration number
        :return: LinearCycle object or None if not found
        """
        return self.cycle_map.get(pt_iteration_number)

    async def ensure_cycle(self, pt_iteration, linear_team_id):
        """
        Ensure a cycle exists in Linear, migrating if necessary.

        :param pt_iteration: Pivotal Tracker iteration object
        :param linear_team_id: ID of the Linear team to create the cycle in
        :return: LinearCycle object
        """
        if pt_iteration.number not in self.cycle_map:
            linear_cycle = await self.migrate_cycle(pt_iteration, linear_team_id)
            self.cycle_map[pt_iteration.number] = linear_cycle
        return self.cycle_map[pt_iteration.number]
