# linear/migrators/comment_migrator.py

import os

from ..api import LinearAPI
from ..config import Config
from ..exceptions import CommentMigrationError
from ..logger import logger
from ..models import LinearAttachment, LinearComment
from ..utils import with_progress


class CommentMigrator:
    def __init__(self, linear_api: LinearAPI, user_migrator):
        self.linear_api = linear_api
        self.user_migrator = user_migrator

    @with_progress(desc="Migrating Comments")
    async def migrate_comments(self, pt_comments, linear_issue_id, pbar=None):
        """
        Migrate a list of Pivotal Tracker comments to Linear comments.

        :param pt_comments: List of Pivotal Tracker comment objects from the database
        :param linear_issue_id: ID of the Linear issue to add comments to
        :param pbar: Progress bar object
        :return: List of created Linear comment IDs
        """
        logger.info(f"Starting migration for {len(pt_comments)} comments")
        if pbar:
            pbar.total = len(pt_comments)
            pbar.refresh()

        migrated_comments = []

        for pt_comment in pt_comments:
            try:
                linear_comment = await self.migrate_comment(pt_comment, linear_issue_id)
                migrated_comments.append(linear_comment.id)
                if pbar:
                    pbar.update(1)
            except CommentMigrationError as e:
                logger.warning(f"Failed to migrate comment {pt_comment.id}: {str(e)}")
                # Continue with the next comment

        logger.info(
            f"Comment migration completed. Migrated {len(migrated_comments)} comments"
        )
        return migrated_comments

    async def migrate_comment(self, pt_comment, linear_issue_id):
        """
        Migrate a single Pivotal Tracker comment to a Linear comment.

        :param pt_comment: Pivotal Tracker comment object from the database
        :param linear_issue_id: ID of the Linear issue to add the comment to
        :return: LinearComment object
        """
        logger.info(f"Migrating comment: {pt_comment.id}")

        try:
            # Get the Linear user ID for the comment author
            linear_user = self.user_migrator.get_linear_user(pt_comment.person_id)
            user_id = linear_user.id if linear_user else None

            # Prepare the comment body
            comment_body = f"[Migrated from Pivotal Tracker]\n\n{pt_comment.text}"

            # Create the comment in Linear
            linear_comment_data = await self.linear_api.create_comment(
                issue_id=linear_issue_id, body=comment_body
            )

            # Create LinearComment object
            linear_comment = LinearComment(
                id=linear_comment_data["id"],
                body=linear_comment_data["body"],
                user_id=user_id,
                created_at=pt_comment.created_at,
                issue_id=linear_issue_id,
            )

            # Handle attachments
            if pt_comment.file_attachments:
                await self.migrate_attachments(
                    pt_comment.file_attachments, linear_issue_id
                )

            return linear_comment

        except Exception as e:
            raise CommentMigrationError(
                f"Failed to migrate comment {pt_comment.id}: {str(e)}"
            )

    async def migrate_attachments(self, pt_attachments, linear_issue_id):
        """
        Migrate Pivotal Tracker attachments to Linear.

        :param pt_attachments: List of Pivotal Tracker attachment objects
        :param linear_issue_id: ID of the Linear issue to add attachments to
        """
        for pt_attachment in pt_attachments:
            try:
                # Construct the full file path
                file_path = Config.get_attachment_path(pt_attachment.file_path)

                # Check if the file exists
                if not os.path.exists(file_path):
                    logger.warning(f"Attachment file not found: {file_path}")
                    continue

                # Create the attachment in Linear
                linear_attachment_data = await self.linear_api.create_attachment(
                    issue_id=linear_issue_id,
                    title=pt_attachment.filename,
                    url=file_path,  # Linear API will handle the file upload
                )

                # Create LinearAttachment object
                linear_attachment = LinearAttachment(
                    id=linear_attachment_data["id"],
                    title=linear_attachment_data["title"],
                    url=linear_attachment_data["url"],
                    issue_id=linear_issue_id,
                )

                logger.info(f"Migrated attachment: {linear_attachment.title}")

            except Exception as e:
                logger.warning(
                    f"Failed to migrate attachment {pt_attachment.filename}: {str(e)}"
                )
