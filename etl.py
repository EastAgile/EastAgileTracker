# etl.py

import asyncio
import os
import shutil
import sys

from tqdm import tqdm

from api import PivotalTrackerAPI
from config import Config
from database import (
    add_or_update,
    add_person_to_project,
    get_db,
    get_or_create_iteration,
    get_or_create_person,
    parse_datetime,
)
from models import (
    Blocker,
    Comment,
    Epic,
    FileAttachment,
    Iteration,
    Label,
    Person,
    Project,
    Story,
    Task,
)
from utils import get_processed_projects, mark_project_as_processed

# Get the terminal width
terminal_width = shutil.get_terminal_size().columns


async def process_project_memberships(api, db, project_id):
    memberships = await api.get_project_memberships(project_id)
    for membership in memberships:
        person_data = membership["person"]
        person = add_or_update(db, Person, **person_data)
        add_person_to_project(db, person.id, project_id)


async def process_iterations(api, db, project_id):
    iterations = await api.get_iterations(project_id)
    for iteration_data in iterations:
        iteration_number = iteration_data["number"]
        iteration = get_or_create_iteration(db, project_id, iteration_number)

        # Update iteration details
        iteration.start = parse_datetime(iteration_data.get("start"))
        iteration.finish = parse_datetime(iteration_data.get("finish"))
        iteration.kind = iteration_data.get("kind")
        iteration.velocity = iteration_data.get("velocity")
        iteration.team_strength = iteration_data.get("team_strength")
        iteration.length = iteration_data.get("length")

        # Extract stories from iteration data
        stories_data = iteration_data.pop("stories", [])

        # Process stories
        for story_data in stories_data:
            story_data["iteration_id"] = iteration.id
            add_or_update(db, Story, **story_data)


async def process_file_attachment(api, db, attachment_data, comment, project_id):
    file_content = await api.download_file(attachment_data["download_url"])
    filename = f"{attachment_data['id']}_{attachment_data['filename']}"
    relative_path = os.path.join(str(project_id), str(comment.story_id), filename)
    full_path = Config.get_attachment_path(relative_path)

    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, "wb") as f:
        f.write(file_content)

    attachment_data["file_path"] = relative_path
    attachment_data["comment_id"] = comment.id
    add_or_update(db, FileAttachment, **attachment_data)


async def process_story(api, db, project_id, story_data, pbar):
    story_id = story_data["id"]
    story_name = story_data["name"]

    # Update the progress bar description with the current story information
    pbar.set_description(f"Processing: {story_id} - {story_name[:50]}...")

    # Extract and process labels before adding the story
    labels_data = story_data.pop("labels", [])

    # Add or update the story
    try:
        story = add_or_update(db, Story, **story_data)
    except Exception as e:
        print(f"Error processing story: {story_data}")
        print(str(e))
        return

    # Process iterations
    if "current_iteration" in story_data:
        iteration_number = story_data["current_iteration"]
        iteration = get_or_create_iteration(db, project_id, iteration_number)
        story.iteration = iteration

    # Process labels
    for label_data in labels_data:
        try:
            label = add_or_update(db, Label, **label_data)
            if label not in story.labels:
                story.labels.append(label)
        except Exception as e:
            print(f"Error processing story label: {label_data}")
            print(str(e))

    # Load owners
    for owner_id in story_data.get("owner_ids", []):
        owner = get_or_create_person(db, owner_id)
        if owner not in story.owners:
            story.owners.append(owner)
        add_person_to_project(db, owner.id, project_id)

    # Load requester
    requester_id = story_data.get("requested_by_id")
    if requester_id:
        requester = get_or_create_person(db, requester_id)
        story.requested_by = requester
        add_person_to_project(db, requester.id, project_id)

    # Load tasks
    tasks = await api.get_tasks(project_id, story.id)
    for task_data in tasks:
        add_or_update(db, Task, **task_data)

    # Load comments and file attachments
    comments = await api.get_comments(project_id, story.id)
    for comment_data in comments:
        person_id = comment_data.get("person_id")
        if person_id:
            person = get_or_create_person(db, person_id)
            add_person_to_project(db, person.id, project_id)
        comment = add_or_update(db, Comment, **comment_data)
        for attachment_data in comment_data.get("file_attachments", []):
            filename = attachment_data.get("filename", "Unknown file")
            pbar.set_description(f"Downloading: {filename}")
            await process_file_attachment(api, db, attachment_data, comment, project_id)

    # Load blockers
    blockers = await api.get_blockers(project_id, story.id)
    for blocker_data in blockers:
        add_or_update(db, Blocker, **blocker_data)


async def extract_and_load_project(project_data, force_update=False):
    project_id = project_data["id"]
    project_name = project_data["name"]

    processed_projects = get_processed_projects()

    if project_id in processed_projects and not force_update:
        print(f"Skipping project {project_id} - {project_name} (already processed)")
        return

    print(f"\nProcessing project: {project_id} - {project_name}")

    try:
        async with PivotalTrackerAPI() as api:
            # Fetch current velocity
            current_velocity_data = await api.get_project_current_velocity(project_id)
            project_data["current_velocity"] = current_velocity_data.get(
                "current_velocity"
            )

            # Handle start_time
            if "start_time" in project_data:
                project_data["start_date"] = project_data.pop("start_time")

            # Handle time_zone
            if "time_zone" in project_data and isinstance(
                project_data["time_zone"], dict
            ):
                project_data["time_zone"] = project_data["time_zone"].get("olson_name")

            stories = await api.get_stories(project_id)
            labels = await api.get_labels(project_id)
            epics = await api.get_epics(project_id)

            with get_db() as db:
                # Load project
                project = add_or_update(db, Project, **project_data)

                # Process project memberships
                await process_project_memberships(api, db, project_id)

                # Load labels
                print(
                    f"Processing {len(labels)} labels for project {project_id} - {project_name}"
                )
                for label_data in labels:
                    try:
                        add_or_update(db, Label, **label_data)
                    except Exception as e:
                        print(f"Error processing label: {label_data}")
                        print(str(e))

                # Load epics and their associated labels
                print(
                    f"Processing {len(epics)} epics for project {project_id} - {project_name}"
                )
                for epic_data in epics:
                    # Extract the nested label data
                    label_data = epic_data.pop("label", None)
                    if label_data:
                        try:
                            label = add_or_update(db, Label, **label_data)
                            epic_data["label_id"] = label.id
                        except Exception as e:
                            print(f"Error processing epic label: {label_data}")
                            print(str(e))

                    try:
                        add_or_update(db, Epic, **epic_data)
                    except Exception as e:
                        print(f"Error processing epic: {epic_data}")
                        print(str(e))

                # Process iterations
                await process_iterations(api, db, project_id)

                # Process stories concurrently with progress bar
                print(
                    f"Processing {len(stories)} stories for project {project_id} - {project_name}"
                )
                story_semaphore = asyncio.Semaphore(
                    8
                )  # Limit to 8 concurrent story processes

                async def process_story_with_semaphore(story_data, pbar):
                    async with story_semaphore:
                        await process_story(api, db, project_id, story_data, pbar)

                with tqdm(
                    total=len(stories),
                    desc=f"Stories for {project_id} - {project_name}",
                    unit="story",
                ) as pbar:

                    async def process_and_update(story_data):
                        await process_story_with_semaphore(story_data, pbar)
                        pbar.update(1)

                    story_tasks = [
                        asyncio.create_task(process_and_update(story_data))
                        for story_data in stories
                    ]
                    await asyncio.gather(*story_tasks)

                # After processing all stories, move to the next line
                print()

                db.commit()

        mark_project_as_processed(project_id)
        print(f"Successfully processed project {project_id} - {project_name}")
    except Exception as e:
        print(f"Error processing project {project_id}: {str(e)}")


async def extract_and_load_all_projects(force_update=False):
    async with PivotalTrackerAPI() as api:
        projects = await api.get_all_projects()
        for project_data in tqdm(projects, desc="Processing projects"):
            await extract_and_load_project(project_data, force_update)


async def run_etl(force_update=False):
    await extract_and_load_all_projects(force_update)


if __name__ == "__main__":
    asyncio.run(run_etl())
