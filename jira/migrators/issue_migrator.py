# jira/migrators/issue_migrator.py

from ..api import JiraAPI
from ..config import Config
from ..exceptions import IssueMigrationError
from ..logger import logger
from ..models import JiraEpic, JiraIssue, JiraIssueType, JiraStatus, JiraSubTask
from ..utils import with_progress
from .user_migrator import UserMigrator


class IssueMigrator:
    def __init__(self, jira_api: JiraAPI, user_migrator: UserMigrator):
        self.jira_api = jira_api
        self.user_migrator = user_migrator
        self.issue_type_map = {"feature": "Story", "bug": "Bug", "chore": "Task"}
        self.priority_map = Config.JIRA_PRIORITY_MAP
        self.story_points_field = Config.JIRA_STORY_POINTS_FIELD
        self.status_map = {
            "unstarted": "Unstarted",
            "started": "Started",
            "finished": "Finished",
            "delivered": "Delivered",
            "rejected": "Rejected",
            "accepted": "Accepted",
        }

    @with_progress(desc="Migrating Issues")
    async def migrate_issues(self, jira_project, pt_stories, pbar=None):
        """
        Migrate a list of Pivotal Tracker stories to Jira issues.

        :param jira_project: JiraProject object
        :param pt_stories: List of Pivotal Tracker story objects
        :param pbar: Progress bar object
        :return: Dictionary mapping PT story IDs to Jira issue keys
        """
        logger.info(f"Starting migration for {len(pt_stories)} issues")
        if pbar is not None:
            pbar.total = len(pt_stories)
            pbar.refresh()

        migrated_issues = {}

        for pt_story in pt_stories:
            try:
                jira_issue = await self.migrate_issue(jira_project, pt_story)
                migrated_issues[pt_story.id] = jira_issue.key
                if pbar is not None:
                    pbar.update(1)
                logger.info(f"Migrated issue: {jira_issue.key}")
            except IssueMigrationError as e:
                logger.warning(f"Failed to migrate issue {pt_story.id}: {str(e)}")
                # Continue with the next issue

        logger.info(
            f"Issue migration completed. Migrated {len(migrated_issues)} issues"
        )
        return migrated_issues

    async def migrate_issue(self, jira_project, pt_story):
        """
        Migrate a single Pivotal Tracker story to a Jira issue.

        :param jira_project: JiraProject object
        :param pt_story: Pivotal Tracker story object
        :return: JiraIssue object
        """
        logger.info(f"Migrating issue: {pt_story.name}")

        try:
            issue_type = self.issue_type_map.get(pt_story.story_type, "Story")
            status = self.status_map.get(pt_story.current_state.lower(), "Unstarted")

            assignee = (
                self.user_migrator.get_jira_user(pt_story.owner_ids[0])
                if pt_story.owner_ids
                else None
            )
            reporter = (
                self.user_migrator.get_jira_user(pt_story.requested_by_id)
                if pt_story.requested_by_id
                else None
            )

            # replace space in labels with underscore
            issue_labels = [label.replace(" ", "_") for label in pt_story.labels]
            story_points = (
                float(pt_story.estimate) if pt_story.estimate is not None else None
            )

            issue_data = {
                "issuetype": {"name": issue_type},
                "assignee": {"id": assignee.account_id} if assignee else None,
                "reporter": {"id": reporter.account_id} if reporter else None,
                "labels": issue_labels,
                "priority": {"id": self.priority_map.get(pt_story.estimate, "3")},
            }

            created_issue = await self.jira_api.create_issue(
                jira_project.key,
                issue_type,
                pt_story.name,
                pt_story.description,
                issue_data,
            )

            # Update the story points field
            if story_points:
                await self.jira_api.update_issue(
                    created_issue["key"], {Config.JIRA_STORY_POINTS_FIELD: story_points}
                )

            # Set the status
            if status != "Unstarted":
                await self.jira_api.transition_issue(created_issue["key"], status)

            # Migrate tasks
            subtasks = []
            if pt_story.tasks:
                subtask_map = await self.migrate_tasks(
                    created_issue["key"], pt_story.tasks
                )
                subtasks = list(subtask_map.values())

            return JiraIssue(
                key=created_issue["key"],
                project=jira_project,
                summary=pt_story.name,
                issue_type=JiraIssueType(name=issue_type),
                description=pt_story.description,
                assignee=assignee,
                reporter=reporter,
                status=JiraStatus(name=status),
                labels=issue_data["labels"],
                created=pt_story.created_at,
                updated=pt_story.updated_at,
                subtasks=subtasks,
            )

        except Exception as e:
            raise IssueMigrationError(
                f"Failed to migrate issue {pt_story.id}: {str(e)}"
            )

    @with_progress(desc="Migrating Epics")
    async def migrate_epics(self, jira_project, pt_epics, pbar=None):
        logger.info(f"Starting migration for {len(pt_epics)} epics")
        if pbar is not None:
            pbar.total = len(pt_epics)
            pbar.refresh()

        epic_map = {}

        for pt_epic in pt_epics:
            try:
                jira_epic = await self.migrate_epic(jira_project, pt_epic)
                epic_map[pt_epic.label_id] = jira_epic.key
                logger.info(f"Migrated epic: {jira_epic.key}")
                if pbar is not None:
                    pbar.update(1)
            except IssueMigrationError as e:
                logger.warning(f"Failed to migrate epic {pt_epic.id}: {str(e)}")

        logger.info(f"Epic migration completed. Migrated {len(epic_map)} epics")
        return epic_map

    async def migrate_epic(self, jira_project, pt_epic):
        logger.info(f"Migrating epic: {pt_epic.name}")

        try:
            created_epic = await self.jira_api.create_epic(
                jira_project.key, pt_epic.name, pt_epic.description
            )

            return JiraEpic(
                key=created_epic["key"],
                project=jira_project,
                summary=pt_epic.name,
                description=pt_epic.description,
                issue_type=JiraIssueType(name="Epic"),
                created=pt_epic.created_at,
                updated=pt_epic.updated_at,
            )

        except Exception as e:
            raise IssueMigrationError(f"Failed to migrate epic {pt_epic.id}: {str(e)}")

    @with_progress(desc="Processing Blockers")
    async def process_blockers(self, jira_issue_map, pt_stories, pbar=None):
        logger.info("Processing blockers")
        if pbar is not None:
            pbar.total = len(pt_stories)
            pbar.refresh()

        for pt_story in pt_stories:
            for blocker in pt_story.blockers:
                if not blocker.resolved:
                    # get the content of the blocker
                    blocker_content = blocker.description

                    # check if the blocker contains a PT story id starting with # and ending with a space
                    if "#" in blocker_content:
                        blocker_id = blocker_content.split("#")[1].split(" ")[0]
                        if blocker_id.isdigit():
                            blocker_id = int(blocker_id)
                            if (
                                blocker_id in jira_issue_map
                                and pt_story.id in jira_issue_map
                            ):
                                try:
                                    await self.jira_api.create_blocker_link(
                                        jira_issue_map[blocker_id],
                                        jira_issue_map[pt_story.id],
                                    )
                                    logger.info(
                                        f"Created blocker link: {jira_issue_map[blocker_id]} blocks {jira_issue_map[pt_story.id]}"
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to create blocker link: {str(e)}"
                                    )
            if pbar is not None:
                pbar.update(1)

        logger.info("Blocker processing completed")

    @with_progress(desc="Linking Issues to Epics")
    async def link_issues_to_epics(
        self, jira_issue_map, epic_map, pt_stories, pt_epics, label_mapping, pbar=None
    ):
        logger.info("Linking issues to epics")
        if pbar is not None:
            pbar.total = len(pt_stories)
            pbar.refresh()

        # Create a mapping of label_id to epic_key
        label_to_epic = {epic: epic_key for epic, epic_key in epic_map.items()}

        for pt_story in pt_stories:
            jira_issue_key = jira_issue_map.get(pt_story.id)
            if not jira_issue_key:
                continue

            # Check if any of the story's labels correspond to an epic
            for label_name in pt_story.labels:
                label_id = label_mapping.get(label_name)
                if label_id in label_to_epic:
                    epic_key = label_to_epic[label_id]
                    try:
                        await self.jira_api.link_issue_to_epic(jira_issue_key, epic_key)
                        logger.info(f"Linked issue {jira_issue_key} to epic {epic_key}")
                        break  # Link to the first matching epic and then stop
                    except Exception as e:
                        logger.warning(
                            f"Failed to link issue {jira_issue_key} to epic {epic_key}: {str(e)}"
                        )
            if pbar is not None:
                pbar.update(1)

        logger.info("Issue to epic linking completed")

    async def migrate_tasks(self, jira_issue_key, pt_tasks):
        """
        Migrate Pivotal Tracker tasks to Jira subtasks.

        :param jira_issue_key: Key of the parent Jira issue
        :param pt_tasks: List of Pivotal Tracker task objects
        :return: Dictionary mapping PT task IDs to Jira subtask keys
        """
        logger.info(f"Migrating {len(pt_tasks)} tasks for issue {jira_issue_key}")
        subtask_map = {}

        for pt_task in pt_tasks:
            try:
                jira_subtask = await self.migrate_task(jira_issue_key, pt_task)
                subtask_map[pt_task.id] = jira_subtask.key
                logger.info(f"Migrated task: {jira_subtask.key}")
            except Exception as e:
                logger.warning(f"Failed to migrate task {pt_task.id}: {str(e)}")

        return subtask_map

    async def migrate_task(self, parent_issue_key, pt_task):
        """
        Migrate a single Pivotal Tracker task to a Jira subtask.

        :param parent_issue_key: Key of the parent Jira issue
        :param pt_task: Pivotal Tracker task object
        :return: JiraSubTask object
        """
        logger.info(f"Migrating task: {pt_task.description}")

        try:
            created_subtask = await self.jira_api.create_subtask(
                parent_issue_key, pt_task.description
            )

            # If the task is complete, update its status
            if pt_task.complete:
                await self.jira_api.transition_issue(created_subtask["key"], "Finished")

            return JiraSubTask(
                key=created_subtask["key"],
                summary=pt_task.description,
                status="Done" if pt_task.complete else "To Do",
                parent_key=parent_issue_key,
            )

        except Exception as e:
            raise IssueMigrationError(f"Failed to migrate task {pt_task.id}: {str(e)}")
