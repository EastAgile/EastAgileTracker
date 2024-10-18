# database.py

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.types import DateTime

from config import Config
from models import Base, Iteration, Person, Project

# Create the engine
engine = create_engine(Config.get_db_url(), echo=False)

# Create a sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Session:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def parse_datetime(date_string):
    if date_string:
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
    return None


def get_or_create_person(session, person_id, **kwargs):
    """Get an existing person or create a new one if it doesn't exist."""
    person = session.query(Person).get(person_id)
    if not person:
        person = Person(id=person_id, **kwargs)
        session.add(person)
    else:
        # Update existing person data
        for key, value in kwargs.items():
            setattr(person, key, value)
    session.flush()
    return person


def get_or_create_iteration(session, project_id, iteration_number):
    iteration = (
        session.query(Iteration)
        .filter_by(project_id=project_id, number=iteration_number)
        .first()
    )
    if not iteration:
        iteration = Iteration(project_id=project_id, number=iteration_number)
        session.add(iteration)
        session.flush()
    return iteration


def filter_model_data(model, data):
    """Filter out keys from data that are not columns in the model and convert data types."""
    columns = inspect(model).columns
    filtered_data = {}
    for k, v in data.items():
        if k in columns.keys():
            if isinstance(columns[k].type, DateTime) and isinstance(v, str):
                filtered_data[k] = parse_datetime(v)
            elif k == "time_zone" and isinstance(v, dict):
                filtered_data[k] = v.get("olson_name")
            else:
                filtered_data[k] = v
    return filtered_data


def add_or_update(session: Session, model, **kwargs):
    """Add a new record or update an existing one."""
    filtered_kwargs = filter_model_data(model, kwargs)
    instance = session.query(model).filter_by(id=filtered_kwargs["id"]).first()
    if instance:
        for key, value in filtered_kwargs.items():
            setattr(instance, key, value)
    else:
        instance = model(**filtered_kwargs)
        try:
            session.add(instance)
            session.flush()
        except IntegrityError:
            session.rollback()
            existing = session.query(model).filter_by(id=filtered_kwargs["id"]).first()
            if existing:
                for key, value in filtered_kwargs.items():
                    setattr(existing, key, value)
            else:
                raise
    return instance


def add_person_to_project(session: Session, person_id: int, project_id: int):
    """Add a person to a project's access list."""
    person = session.query(Person).get(person_id)
    project = session.query(Project).get(project_id)
    if person and project:
        if project not in person.projects:
            person.projects.append(project)
            session.commit()
    else:
        raise ValueError("Person or Project not found")


def get_project_members(session: Session, project_id: int):
    """Get all members of a project."""
    project = session.query(Project).get(project_id)
    if project:
        return project.members
    else:
        raise ValueError("Project not found")


def bulk_insert_or_update(session: Session, model, data):
    """Bulk insert or update records."""
    for item in data:
        add_or_update(session, model, **item)
    session.commit()


def get_or_create(session: Session, model, **kwargs):
    """Get an existing record or create a new one if it doesn't exist."""
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance


def clear_db():
    """Clear all data from the database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
