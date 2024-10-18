# models.py

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

project_access = Table(
    "project_access",
    Base.metadata,
    Column("person_id", Integer, ForeignKey("persons.id")),
    Column("project_id", Integer, ForeignKey("projects.id")),
)


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    description = Column(String(140))
    public = Column(Boolean)
    version = Column(Integer)
    week_start_day = Column(String)
    point_scale = Column(String(255))
    point_scale_is_custom = Column(Boolean)
    bugs_and_chores_are_estimatable = Column(Boolean)
    automatic_planning = Column(Boolean)
    enable_tasks = Column(Boolean)
    start_date = Column(DateTime)
    time_zone = Column(String)
    velocity_averaged_over = Column(Integer)
    number_of_done_iterations_to_show = Column(Integer)
    has_google_domain = Column(Boolean)
    enable_incoming_emails = Column(Boolean)
    initial_velocity = Column(Integer)
    project_type = Column(String)
    current_iteration_number = Column(Integer)
    current_velocity = Column(Integer)
    account_id = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    stories = relationship("Story", back_populates="project")
    epics = relationship("Epic", back_populates="project")
    labels = relationship("Label", back_populates="project")
    members = relationship(
        "Person", secondary=project_access, back_populates="projects"
    )
    iterations = relationship("Iteration", back_populates="project")


class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    initials = Column(String)
    username = Column(String)

    owned_stories = relationship(
        "Story", secondary="story_owners", back_populates="owners"
    )
    projects = relationship(
        "Project", secondary=project_access, back_populates="members"
    )


story_owner = Table(
    "story_owners",
    Base.metadata,
    Column("story_id", Integer, ForeignKey("stories.id")),
    Column("person_id", Integer, ForeignKey("persons.id")),
)

story_label = Table(
    "story_labels",
    Base.metadata,
    Column("story_id", Integer, ForeignKey("stories.id")),
    Column("label_id", Integer, ForeignKey("labels.id")),
)


class Iteration(Base):
    __tablename__ = "iterations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    number = Column(Integer, nullable=False)
    length = Column(Integer)
    start = Column(DateTime)
    finish = Column(DateTime)
    kind = Column(String)
    velocity = Column(Float)
    team_strength = Column(Float)

    project = relationship("Project", back_populates="iterations")
    stories = relationship("Story", back_populates="iteration")


class Story(Base):
    __tablename__ = "stories"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    story_type = Column(String, nullable=False)
    current_state = Column(String, nullable=False)
    estimate = Column(Float)
    accepted_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)
    requested_by_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    story_priority = Column(String)
    iteration_id = Column(Integer, ForeignKey("iterations.id"))

    project = relationship("Project", back_populates="stories")
    requested_by = relationship("Person", foreign_keys=[requested_by_id])
    owners = relationship(
        "Person", secondary=story_owner, back_populates="owned_stories"
    )
    labels = relationship("Label", secondary=story_label, back_populates="stories")
    comments = relationship("Comment", back_populates="story")
    blockers = relationship("Blocker", back_populates="story")
    tasks = relationship("Task", back_populates="story")
    iteration = relationship("Iteration", back_populates="stories")


class Label(Base):
    __tablename__ = "labels"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    project = relationship("Project", back_populates="labels")
    stories = relationship("Story", secondary=story_label, back_populates="labels")


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    text = Column(String)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)

    story = relationship("Story", back_populates="comments")
    person = relationship("Person")
    file_attachments = relationship("FileAttachment", back_populates="comment")


class FileAttachment(Base):
    __tablename__ = "file_attachments"
    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey("comments.id"))
    filename = Column(String)
    content_type = Column(String)
    size = Column(Integer)
    download_url = Column(String)
    uploader_id = Column(Integer, ForeignKey("persons.id"))
    created_at = Column(DateTime)
    file_path = Column(String)  # Relative path to the file

    comment = relationship("Comment", back_populates="file_attachments")
    uploader = relationship("Person")


class Epic(Base):
    __tablename__ = "epics"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    label_id = Column(Integer, ForeignKey("labels.id"), nullable=False)
    name = Column(String)
    description = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    project = relationship("Project", back_populates="epics")
    label = relationship("Label")


class Blocker(Base):
    __tablename__ = "blockers"
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=True)
    description = Column(String, nullable=False)
    resolved = Column(Boolean, nullable=False)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    story = relationship("Story", back_populates="blockers")
    person = relationship("Person")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    description = Column(String, nullable=False)
    complete = Column(Boolean, default=False)
    position = Column(Integer)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)

    story = relationship("Story", back_populates="tasks")


tasks = relationship("Task", back_populates="story")
