from typing import List, Dict
import datetime
import random
from sqlalchemy.orm import Session
from . import models


def create_assignments(participants: List[int], previous_assignments: Dict[int, int]):

    # Initialize assignments dictionary
    assignments = {}

    # Create set of available receivers
    available_receivers = set(participants)

    for giver in participants:

        # Remove reference giver from set of available receivers
        # Cannot be assigned yourself
        possible_receivers = available_receivers - {giver}

        # Remove the previous year's assignment from available receivers if it exists
        if giver in previous_assignments:
            possible_receivers -= {previous_assignments[giver]}

        # If no valid receivers, reset and try again
        # Starts over from the beginning to make random draws from the top
        # todo: add max attempts safety measure
        if not possible_receivers:
            return create_assignments(participants, previous_assignments)

        # Make random choice from possible receivers and add it to the assignments dictionary
        receiver = random.choice(list(possible_receivers))
        assignments[giver] = receiver
        available_receivers.remove(receiver)

    return assignments


def assign_secret_snakes(db: Session, participants: List[int], year: int):

    # Query for prior year assignments
    previous_assignments = db.query(models.Assignment).filter(models.Assignment.year == year - 1).all()

    # Format previous assignments as dictionary
    # Key: assignee user id, Value: assigned user id
    prev_assign_dict = {
        previous_assignment.assignee_user_id: previous_assignment.assigned_user_id for previous_assignment in
        previous_assignments
    }

    # Create assignments
    assignments = create_assignments(participants, prev_assign_dict)

    # Save assignments to database
    for assignee_user_id, assigned_user_id in assignments.items():
        new_assignment = models.Assignment(
            assignee_user_id=assignee_user_id,
            assigned_user_id=assigned_user_id,
            year=year,
            created_at=datetime.datetime.now()
        )
        db.add(new_assignment)
    db.commit()

    return assignments

