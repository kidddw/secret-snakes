import datetime
from sqlalchemy.orm import Session
from sqlalchemy.sql import null

from . import models


def initialize_config(db: Session):
    """
    If the config table is missing certain values, initialize those
    """
    initialize_assignment_year(db)
    initialize_allow_registration(db)


def initialize_assignment_year(db: Session):
    """
    If the config is missing assignment_year, initialize it as current year
    """

    # Check if 'assignment_year' exists in the config
    assignment_year_config = db.query(models.Config).filter(models.Config.key == 'assignment_year').first()

    if not assignment_year_config:

        # Add 'assignment_year' to the config
        current_year = str(datetime.datetime.now().year)
        now = datetime.datetime.utcnow()
        new_config = models.Config(key='assignment_year', value=current_year, start_time=now, end_time=None)
        db.add(new_config)
        db.commit()


def initialize_allow_registration(db: Session):
    """
    If the config is missing assignment_year, initialize it as current year
    """

    # Check if 'allow_registration' exists in the config
    allow_registration_config = db.query(models.Config).filter(models.Config.key == 'allow_registration').first()

    if not allow_registration_config:

        # Add 'allow_registration' to the config
        now = datetime.datetime.utcnow()
        new_config = models.Config(key='allow_registration', value="True", start_time=now, end_time=None)
        db.add(new_config)
        db.commit()


def get_config(db: Session):
    """
    Retrieves the active config as a dictionary of key-value pairs.
    """
    config_dict = {}

    # Retrieve current config values
    current_config = db.query(models.Config).filter(
        models.Config.end_time == null()
    ).all()

    # Check for duplicates
    keys = [config_item.key for config_item in current_config]
    if len(keys) != len(set(keys)):
        raise ValueError("Multiple active configs found for the same key")

    # Create config dictionary
    for config_item in current_config:
        config_dict[config_item.key] = config_item.value

    return config_dict


def set_config(db: Session, key: str, value: str):
    """
    Sets a new config value, expiring the old one.
    """
    now = datetime.datetime.utcnow()

    # Get the current active setting
    current_setting = db.query(models.Config).filter(
        models.Config.key == key,
        models.Config.end_time == null()
    ).first()

    if current_setting:

        # Expire the current setting
        current_setting.end_time = now
        db.add(current_setting)

    # Create a new setting
    new_setting = models.Config(key=key, value=value, start_time=now, end_time=None)
    db.add(new_setting)

    db.commit()
    return True
