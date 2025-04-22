from typing import List
import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app import schemas
from app.models import (
    User,
    Assignment,
    Tip
)


def count_tips_for_current_assignment(
        db: Session,
        current_user_id: int,
        assignment_year: int
):
    """
    Count number of tips for a user's current assignment.
    """
    tip_count = db.query(func.count(Tip.id)).join(
        Assignment,
        and_(
            Assignment.assigned_user_id == Tip.subject_user_id,
            Assignment.year == Tip.year
        )
    ).filter(
        Assignment.assignee_user_id == current_user_id,
        Assignment.year == assignment_year
    ).scalar()
    return tip_count


def create_tip(
        tip: schemas.TipCreate,
        db: Session,
        current_user_id: int,
):
    """
    Create a new tip

    1. Take in some tip input
    2. Identify the current user automatically
    3. Add tip to tips table
    """

    # Initialize Tip table-object instance using the provided details
    db_tip = Tip(
        content=tip.content,
        year=tip.year,
        subject_user_id=tip.subject_user_id,
        contributor_user_id=current_user_id,
        created_at=datetime.datetime.now()
    )

    # Add new row to the tips table for this new assignment
    db.add(db_tip)
    db.commit()
    db.refresh(db_tip)

    return db_tip


def get_tips_for_contributor_user(
        db: Session,
        user_id: int,
        assignment_year: int
) -> List[schemas.Tip]:
    """
    Retrieve all tips for a specific contributing user.
    """
    tips_for_user = db.query(Tip).filter(
        Tip.contributor_user_id == user_id,
        Tip.year == assignment_year
    ).order_by(desc(Tip.created_at)).all()
    return tips_for_user


def get_tips_for_subject_user(
        db: Session,
        user_id: int,
        assignment_year: int
) -> List[schemas.Tip]:
    """
    Retrieve all tips for a specific contributing user.
    """
    tips_for_user = db.query(Tip).filter(
        Tip.subject_user_id == user_id,
        Tip.year == assignment_year
    ).order_by(desc(Tip.created_at)).all()
    return tips_for_user


def get_tip(db: Session, tip_id: int):
    """
    Retrieve a specific tip by its ID.
    """
    return db.query(Tip).filter(Tip.id == tip_id).first()


def delete_tip(db: Session, tip_id: int, current_user_id: int):
    """
    Delete a tip. Only the creator of the tip or an admin can delete it.
    """

    # Query for the tip. If not present, raise exception
    tip = get_tip(db, tip_id)
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")

    # Query for the current user
    user = db.query(User).filter(User.id == current_user_id).first()

    # If (a) user is not admin or (b) tip was not left by current user then raise exception
    if not user.is_admin and tip.contributor_user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this tip")

    # Delete tip in database
    db.delete(tip)
    db.commit()

    return {"message": "Tip deleted successfully"}


def update_tip(db: Session, current_user_id: int, tip_id: int, content: str):
    """
    Update a tip. Only the creator of the tip or an admin can update it.
    """

    # Query for the tip. If not present, raise exception
    db_tip = get_tip(db, tip_id)
    if not db_tip:
        raise HTTPException(status_code=404, detail="Tip not found")

    # Query for the current user
    user = db.query(User).filter(User.id == current_user_id).first()

    # If (a) user is not admin or (b) tip was not left by current user then raise exception
    if not user.is_admin and db_tip.contributor_user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this tip")

    # Update content of Tip to be that of the new Tip
    setattr(db_tip, 'content', content)

    # Write to database
    db.add(db_tip)
    db.commit()
    db.refresh(db_tip)

    return db_tip

