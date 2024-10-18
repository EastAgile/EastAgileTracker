# jira/migrators/user_migrator.py

from ..api import JiraAPI
from ..config import Config
from ..exceptions import UserMigrationError
from ..logger import logger
from ..models import JiraUser
from ..utils import with_progress


class UserMigrator:
    def __init__(self, jira_api: JiraAPI):
        self.jira_api = jira_api
        self.user_map = {}  # Map PT user IDs to Jira user objects

    @with_progress(desc="Migrating Users")
    async def migrate_users(self, pt_users, pbar=None):
        """
        Migrate a list of Pivotal Tracker users to Jira.

        :param pt_users: List of Pivotal Tracker user objects from the database
        :param pbar: Progress bar object
        :return: Dictionary mapping PT user IDs to Jira user objects
        """
        logger.info(f"Starting migration for {len(pt_users)} users")
        if pbar is not None:
            pbar.total = len(pt_users)
            pbar.refresh()

        for pt_user in pt_users:
            try:
                jira_user = await self.migrate_user(pt_user)
                self.user_map[pt_user.id] = jira_user
                if pbar is not None:
                    pbar.update(1)
            except UserMigrationError as e:
                logger.warning(f"Failed to migrate user {pt_user.name}: {str(e)}")
                # Continue with the next user

        logger.info(f"User migration completed. Migrated {len(self.user_map)} users")
        return self.user_map

    async def migrate_user(self, pt_user):
        """
        Migrate a single Pivotal Tracker user to Jira.

        :param pt_user: Pivotal Tracker user object from the database
        :return: JiraUser object
        """
        logger.info(f"Migrating user: {pt_user.name}")

        try:
            # Check if user already exists in Jira
            existing_user = await self.jira_api.get_user(pt_user.email)
            if len(existing_user) == 1:
                logger.info(f"User {pt_user.name} already exists in Jira")
                user = existing_user[0]
                return JiraUser(
                    email=pt_user.email,
                    display_name=user["displayName"],
                    account_id=user["accountId"],
                    active=user["active"],
                )
            elif len(existing_user) > 1:
                raise UserMigrationError(
                    f"Found multiple users with email {pt_user.email} in Jira"
                )

            # Create new user in Jira as inactive
            new_user = await self.jira_api.create_user(
                email=pt_user.email,
            )
            logger.info(f"Created new user in Jira: {new_user['displayName']}")

            return JiraUser(
                email=new_user["emailAddress"],
                display_name=new_user["displayName"],
                account_id=new_user["accountId"],
                active=True,
            )

        except Exception as e:
            raise UserMigrationError(f"Failed to migrate user {pt_user.name}: {str(e)}")

    def get_jira_user(self, pt_user_id):
        """
        Get the Jira user object for a given Pivotal Tracker user ID.

        :param pt_user_id: Pivotal Tracker user ID
        :return: JiraUser object or None if not found
        """
        return self.user_map.get(pt_user_id)

    @with_progress(desc="Activating User")
    async def activate_user(self, email, pbar=None):
        """
        Activate a user in Jira.

        :param email: Email of the user to activate
        :param pbar: Progress bar object
        :return: Updated JiraUser object
        """
        try:
            updated_user = await self.jira_api.update_user(email, active=True)
            logger.info(f"Activated user in Jira: {email}")

            # Update the user in our user_map
            for pt_id, jira_user in self.user_map.items():
                if jira_user.email == email:
                    self.user_map[pt_id] = JiraUser(
                        email=updated_user["emailAddress"],
                        display_name=updated_user["displayName"],
                        account_id=updated_user["accountId"],
                        active=True,
                    )
                    break

            if pbar is not None:
                pbar.update(1)

            return self.user_map[pt_id]
        except Exception as e:
            logger.error(f"Failed to activate user {email}: {str(e)}")
            raise UserMigrationError(f"Failed to activate user {email}: {str(e)}")
