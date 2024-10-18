# jira/migrators/comment_migrator.py

import os

import aiohttp

from ..api import JiraAPI
from ..exceptions import CommentMigrationError
from ..logger import logger
from ..models import JiraAttachment, JiraComment
from ..utils import with_progress
from .user_migrator import UserMigrator


class CommentMigrator:
    def __init__(self, jira_api: JiraAPI, user_migrator: UserMigrator):
        self.jira_api = jira_api
        self.user_migrator = user_migrator
        self.base_directory = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

    @with_progress(desc="Migrating Comments")
    async def migrate_comments(self, jira_issue_key, pt_comments, pbar=None):
        """
        Migrate comments from a Pivotal Tracker story to a Jira issue.

        :param jira_issue_key: Key of the Jira issue
        :param pt_comments: List of Pivotal Tracker comment objects
        :param pbar: Progress bar object
        :return: List of created Jira comment IDs
        """
        logger.info(
            f"Starting migration for {len(pt_comments)} comments on issue {jira_issue_key}"
        )
        if pbar is not None:
            pbar.total = len(pt_comments)
            pbar.refresh()

        migrated_comments = []

        for pt_comment in pt_comments:
            try:
                if len(pt_comment.attachments) == 0:
                    # Migrate comment without attachments
                    jira_comment = await self.migrate_comment(
                        jira_issue_key, pt_comment, []
                    )
                    migrated_comments.append(jira_comment.id)
                else:
                    # Migrate attachments for this comment
                    attachments = []
                    for pt_attachment in pt_comment.attachments:
                        jira_attachment = await self.migrate_attachment(
                            jira_issue_key, pt_attachment
                        )
                        attachments.append(jira_attachment)

                    # Then create the comment referencing the attachments
                    jira_comment = await self.migrate_comment(
                        jira_issue_key, pt_comment, attachments
                    )
                    migrated_comments.append(jira_comment.id)
                if pbar is not None:
                    pbar.update(1)
            except CommentMigrationError as e:
                logger.warning(f"Failed to migrate comment {pt_comment.id}: {str(e)}")
                # Continue with the next comment

        logger.info(
            f"Comment migration completed. Migrated {len(migrated_comments)} comments"
        )
        return migrated_comments

    async def migrate_comment(self, jira_issue_key, pt_comment, attachments):
        """
        Migrate a single Pivotal Tracker comment to a Jira issue comment.

        :param jira_issue_key: Key of the Jira issue
        :param pt_comment: Pivotal Tracker comment object
        :param attachment_file_names: List of attachment file names
        :return: JiraComment object
        """
        logger.info(f"Migrating comment: {pt_comment.id}")

        try:
            author = self.user_migrator.get_jira_user(pt_comment.person_id)

            comment_body = f"[Migrated from Pivotal Tracker]\n\n{pt_comment.text}"

            if author:
                comment_body = f"Comment by {author.display_name}:\n\n{comment_body}"

            if len(attachments) > 0:
                comment_body += "\n\nAttachments:\n"
                for attachment in attachments:
                    comment_body += f"!{attachment.filename}! "

            created_comment = await self.jira_api.create_comment(
                jira_issue_key, comment_body
            )

            return JiraComment(
                id=str(created_comment["id"]),
                body=created_comment["body"],
                author=author,
                created=pt_comment.created_at,
                updated=pt_comment.updated_at,
            )

        except Exception as e:
            raise CommentMigrationError(
                f"Failed to migrate comment {pt_comment.id}: {str(e)}"
            )

    async def migrate_attachment(self, jira_issue_key, pt_attachment):
        """
        Migrate a single Pivotal Tracker attachment to a Jira comment attachment.

        :param jira_issue_key: Key of the Jira issue
        :param pt_attachment: Pivotal Tracker attachment object
        :return: JiraAttachment object
        """
        logger.info(f"Migrating attachment: {pt_attachment.filename}")

        try:
            uploader = self.user_migrator.get_jira_user(pt_attachment.uploader_id)

            # Construct the full file path starting from the base directory with 'attachments' folder
            full_path = os.path.join(
                self.base_directory, "attachments", pt_attachment.file_path
            )

            form_data = aiohttp.FormData()
            form_data.add_field(
                "file",
                open(full_path, "rb"),
                filename=pt_attachment.filename,
                content_type="application/octet-stream",
            )

            created_attachment = await self.jira_api.add_attachment_to_issue(
                jira_issue_key, form_data
            )

            # Check if created_attachment is a list and get the first item if so
            if isinstance(created_attachment, list) and created_attachment:
                created_attachment = created_attachment[0]

            # Safely access the attachment data
            attachment_id = created_attachment.get("id")
            attachment_filename = created_attachment.get("filename")
            attachment_size = created_attachment.get("size")

            if not all([attachment_id, attachment_filename, attachment_size]):
                raise ValueError("Incomplete attachment data received from Jira API")

            return JiraAttachment(
                filename=created_attachment["filename"],
                size=created_attachment["size"],
            )

        except Exception as e:
            raise CommentMigrationError(
                f"Failed to migrate attachment {pt_attachment.filename}: {str(e)}"
            )
