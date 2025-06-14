from typing import List, Dict
import logging
import datetime
import random
from sqlalchemy.orm import Session

from app.emails import send_assignment_email
from app.models import (
    User,
    Assignment
)


# Adding logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    previous_assignments = db.query(Assignment).filter(Assignment.year == year - 1).all()

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
        new_assignment = Assignment(
            assignee_user_id=assignee_user_id,
            assigned_user_id=assigned_user_id,
            year=year,
            created_at=datetime.datetime.now()
        )
        db.add(new_assignment)
    db.commit()

    # Send email notifications to participants about their assignments
    send_email_notifications(assignments, year, db)

    return assignments


def send_email_notifications(assignments: Dict[int, int], year: int, db: Session):
    """
    Send email notifications to participants about their assignments
    """

    for assignee_user_id, assigned_user_id in assignments.items():

        try:

            # Query for assignee user to get their email
            assignee_user = db.query(User).get(assignee_user_id)
            assignee_email = assignee_user.email

            # Query for assigned user to get their username and shipping info
            assigned_user = db.query(User).get(assigned_user_id)
            assigned_username = assigned_user.username
            assigned_user_shipping_info = {
                "first_name": assigned_user.first_name,
                "last_name": assigned_user.last_name,
                "street_address": assigned_user.shipping_street_address,
                "unit": assigned_user.shipping_unit,
                "city": assigned_user.shipping_city,
                "zipcode": assigned_user.shipping_zipcode,
                "state": assigned_user.shipping_state,
            }

        except Exception as e:
            # Log any errors that occur during the query
            logger.warning(f"Error retrieving user data. Assignee ID: {assignee_user_id}, Assigned ID: {assigned_user_id}, Year: {year}")
            logger.warning(f"Error retrieving user data for assignment: {e}")
            continue

        # to_email, assigned_username, shipping_info, subject=
        subject = f"Your Secret Snakes Assignment for {year}"

        # Pass collected data to the placeholder email sending function
        send_assignment_email(
            to_email=assignee_email,
            assigned_username=assigned_username,
            shipping_info=assigned_user_shipping_info,
            subject=subject
        )
