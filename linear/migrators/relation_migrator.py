# linear/migrators/relation_migrator.py

from ..api import LinearAPI
from ..exceptions import RelationMigrationError
from ..logger import logger
from ..models import LinearIssueRelation
from ..utils import with_progress


class RelationMigrator:
    def __init__(self, linear_api: LinearAPI, issue_migrator):
        self.linear_api = linear_api
        self.issue_migrator = issue_migrator

    @with_progress(desc="Migrating Issue Relations")
    async def migrate_relations(self, pt_stories, pbar=None):
        """
        Migrate relations (blockers) from Pivotal Tracker stories to Linear issue relations.

        :param pt_stories: List of Pivotal Tracker story objects from the database
        :param pbar: Progress bar object
        :return: List of created Linear issue relation IDs
        """
        logger.info(f"Starting migration for relations of {len(pt_stories)} stories")
        if pbar:
            pbar.total = len(pt_stories)
            pbar.refresh()

        migrated_relations = []

        for pt_story in pt_stories:
            try:
                relations = await self.migrate_story_relations(pt_story)
                migrated_relations.extend(relations)
                if pbar:
                    pbar.update(1)
            except RelationMigrationError as e:
                logger.warning(
                    f"Failed to migrate relations for story {pt_story.id}: {str(e)}"
                )
                # Continue with the next story

        logger.info(
            f"Relation migration completed. Migrated {len(migrated_relations)} relations"
        )
        return migrated_relations

    async def migrate_story_relations(self, pt_story):
        """
        Migrate relations for a single Pivotal Tracker story.

        :param pt_story: Pivotal Tracker story object from the database
        :return: List of created LinearIssueRelation objects
        """
        logger.info(f"Migrating relations for story: {pt_story.id}")

        migrated_relations = []

        try:
            linear_issue = self.issue_migrator.get_linear_issue(pt_story.id)
            if not linear_issue:
                logger.warning(
                    f"No corresponding Linear issue found for PT story {pt_story.id}"
                )
                return migrated_relations

            # Handle blockers
            for blocker in pt_story.blockers:
                if blocker.resolved:
                    continue  # Skip resolved blockers

                blocker_story = blocker.story
                linear_blocker_issue = self.issue_migrator.get_linear_issue(
                    blocker_story.id
                )
                if not linear_blocker_issue:
                    logger.warning(
                        f"No corresponding Linear issue found for PT blocker story {blocker_story.id}"
                    )
                    continue

                # Create "blocks" relation in Linear
                relation_data = await self.linear_api.create_issue_relation(
                    issue_id=linear_blocker_issue.id,
                    related_issue_id=linear_issue.id,
                    type="blocks",
                )

                linear_relation = LinearIssueRelation(
                    id=relation_data["id"],
                    issue_id=linear_blocker_issue.id,
                    related_issue_id=linear_issue.id,
                    type="blocks",
                )
                migrated_relations.append(linear_relation)

            # Handle other potential relations here (e.g., "relates to" for stories in the same epic)
            # This would depend on how you want to map other Pivotal Tracker relationships to Linear

        except Exception as e:
            raise RelationMigrationError(
                f"Failed to migrate relations for story {pt_story.id}: {str(e)}"
            )

        return migrated_relations
