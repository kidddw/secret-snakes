from typing import List, Dict
import logging
import datetime
import random
from sqlalchemy.orm import Session

from app.emails import send_assignment_email
from app.models import (
    User,
    Assignment,
    AssignmentExclusion
)


# Adding logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_exclusions(db: Session, year: int) -> Dict[int, List[int]]:
    """
    Fetches the exclusion list for a given year from the database.
    
    Args:
        db (Session): SQLAlchemy database session.
        year (int): The year for which to fetch exclusions.

    Returns:
        Dict[int, List[int]]: A dictionary where keys are giver IDs and values are lists of excluded receiver IDs.
    """
    exclusions = db.query(AssignmentExclusion).filter(AssignmentExclusion.year == year).all()
    exclusion_dict = {}
    
    for exclusion in exclusions:
        if exclusion.giver_user_id not in exclusion_dict:
            exclusion_dict[exclusion.giver_user_id] = []
        exclusion_dict[exclusion.giver_user_id].append(exclusion.excluded_user_id)
    
    return exclusion_dict


def create_assignments(
    participants: List[int],
    previous_assignments: Dict[int, int],
    exclusion_list: Dict[int, List[int]]
):
    """
    Randomly assigns participants to each other, avoiding self-assignment,
    previous year's assignments, and specific exclusions.
    
    Args:
        participants (List[int]): A list of all participant IDs.
        previous_assignments (Dict[int, int]): A dictionary where keys are giver IDs
                                                and values are the receiver IDs from the previous year.
        exclusion_list (Dict[int, List[int]]): A dictionary where keys are giver IDs
                                                and values are lists of receiver IDs to exclude.

    Returns:
        Dict[int, int]: A dictionary of the new assignments, or None if a valid
                        assignment could not be created after multiple attempts.
    """
    
    # Initialize assignments and set a maximum number of attempts
    assignments = {}
    max_attempts = 100
    
    for _ in range(max_attempts):

        # Initialize assignments dictionary
        assignments = {}

        # Create set of available receivers
        available_receivers = set(participants)

        # Shuffle the participants to ensure a more random assignment order
        shuffled_participants = participants.copy()
        random.shuffle(shuffled_participants)

        try:
            for giver in shuffled_participants:

                # Start with all available receivers
                possible_receivers = available_receivers.copy()

                # Rule 1: A user cannot be assigned to themselves
                if giver in possible_receivers:
                    possible_receivers.remove(giver)

                # Rule 2: A user cannot be assigned to their previous year's recipient
                if giver in previous_assignments and previous_assignments[giver] in possible_receivers:
                    possible_receivers.remove(previous_assignments[giver])

                # Rule 3: A user cannot be assigned to anyone on their exclusion list
                if giver in exclusion_list:
                    for excluded_receiver in exclusion_list[giver]:
                        if excluded_receiver in possible_receivers:
                            possible_receivers.remove(excluded_receiver)
                
                # If there are no valid receivers, this attempt has failed. Break and try again.
                if not possible_receivers:
                    raise ValueError("No valid receivers for a participant. Retrying assignment.")
                
                # Randomly select a receiver from the remaining valid options
                receiver = random.choice(list(possible_receivers))
                assignments[giver] = receiver
                available_receivers.remove(receiver)
            
            # If the loop completes successfully, a valid assignment has been found.
            return assignments

        except ValueError:
            # An attempt failed, so the loop will continue to the next iteration.
            continue
    
    # If all attempts fail, return None to indicate an impossible assignment scenario.
    return None


def assign_secret_snakes(db: Session, participants: List[int], year: int):

    # Query for prior year assignments
    previous_assignments = db.query(Assignment).filter(Assignment.year == year - 1).all()

    # Format previous assignments as dictionary
    # Key: assignee user id, Value: assigned user id
    prev_assign_dict = {
        previous_assignment.assignee_user_id: previous_assignment.assigned_user_id for previous_assignment in
        previous_assignments
    }

    # Query for current year's exclusion list
    exclusions = fetch_exclusions(db, year)
        
    # Create assignments
    assignments = create_assignments(participants, prev_assign_dict, exclusions)

    # If assignments could not be created, log an error and return None
    if assignments is None:
        logger.error("Failed to create valid assignments after multiple attempts.")
        return None

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
