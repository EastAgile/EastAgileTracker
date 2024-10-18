# linear/migrators/user_migrator.py

from ..api import LinearAPI
from ..config import Config
from ..exceptions import UserMigrationError
from ..logger import logger
from ..models import LinearUser
from ..utils import with_progress


class UserMigrator:
    def __init__(self, linear_api: LinearAPI):
        self.linear_api = linear_api
        self.linear_team_id = None
        self.user_map = Config.LINEAR_USER_MAP  # Map PT user IDs to Linear user objects

    @with_progress(desc="Migrating Users")
    async def migrate_users(self, pt_users, linear_team_id, pbar=None):
        """
        Migrate a list of Pivotal Tracker users to Linear.

        :param pt_users: List of Pivotal Tracker user objects from the database
        :param pbar: Progress bar object
        :return: Dictionary mapping PT user IDs to Linear user objects
        """
        logger.info(f"Starting migration for {len(pt_users)} users")
        if pbar:
            pbar.total = len(pt_users)
            pbar.refresh()

        self.linear_team_id = linear_team_id

        for pt_user in pt_users:
            try:
                await self.migrate_user(pt_user)
                if pbar:
                    pbar.update(1)
            except UserMigrationError as e:
                logger.warning(f"Failed to migrate user {pt_user.name}: {str(e)}")
                # Continue with the next user

        logger.info(f"User migration completed. Migrated {len(self.user_map)} users")
        return self.user_map

    async def migrate_user(self, pt_user):
        """
        Migrate a single Pivotal Tracker user to Linear.

        :param pt_user: Pivotal Tracker user object from the database
        :return: LinearUser object
        """
        logger.info(f"Migrating user: {pt_user.name}")

        try:
            # Get the linear user
            linear_user = self.get_linear_user(pt_user.id)

            if not linear_user:
                linear_user = await self.linear_api.get_user(pt_user.email)

                if linear_user:
                    linear_user = LinearUser(**linear_user)
                    self.user_map[pt_user.id] = linear_user
                else:
                    # invite the user in Linear, acknowledging that we won't get the account id until they accept
                    await self.linear_api.invite_user(
                        pt_user.email, self.linear_team_id
                    )

            if linear_user:
                # Attempt to add the user to the team
                await self.linear_api.add_user_to_team(
                    linear_user.id, self.linear_team_id
                )

            logger.info(f"User migrated: {pt_user.name}")

        except Exception as e:
            raise UserMigrationError(f"Failed to migrate user {pt_user.name}: {str(e)}")

    def get_linear_user(self, pt_user_id):
        """
        Get the Linear user object for a given Pivotal Tracker user ID.

        :param pt_user_id: Pivotal Tracker user ID
        :return: LinearUser object or None if not found
        """
        return self.user_map.get(pt_user_id)

    async def ensure_user(self, pt_user):
        """
        Ensure a user exists in Linear, migrating if necessary.

        :param pt_user: Pivotal Tracker user object
        :return: LinearUser object
        """
        if pt_user.id not in self.user_map:
            linear_user = await self.migrate_user(pt_user)
            self.user_map[pt_user.id] = linear_user
        return self.user_map[pt_user.id]
