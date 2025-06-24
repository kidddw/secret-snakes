import os
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Assuming your models.py and database.py are structured as provided
# We need to import the Base and models from your application's schema
from app.models import Base, User, Assignment

# --- Database setup (copied from your database.py, ensure consistency) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./secret_snakes.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db_session():
    """
    Returns a SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        return db
    finally:
        # Note: In a real application, you'd typically manage session closing
        # via a dependency injection system (like FastAPI's Depends) or a context manager.
        # For a standalone script, returning and manually closing after use is fine.
        pass # The 'finally' block can close, but let's manage it explicitly in main() for clarity

def init_db_if_not_exists():
    """
    Initializes the database by creating tables if the database file does not exist.
    Ensure this is called before attempting to add data if the DB might not exist.
    """
    # Using SQLALCHEMY_DATABASE_URL to get the actual database file path
    db_file_path = SQLALCHEMY_DATABASE_URL.split('///')[1]

    if not os.path.exists(db_file_path):
        Base.metadata.create_all(bind=engine)
        print(f"Database '{db_file_path}' created.")
    else:
        print(f"Database '{db_file_path}' already exists.")

# --- Main script logic ---

def add_historical_assignments(historical_data: dict):
    """
    Adds historical assignment data to the database.

    Args:
        historical_data (dict): A dictionary where keys are years (int)
                                and values are dictionaries mapping
                                assigned_username to assignee_username.
                                Example: {2022: {'d-dawg': 'brinkle', ...}}
    """
    db = None # Initialize db to None
    try:
        db = get_db_session()
        print("\nStarting to add historical assignments...")

        # Helper dictionary to cache user IDs to avoid repeated DB queries
        user_id_cache = {}

        for year, assignments_for_year in historical_data.items():
            print(f"\nProcessing assignments for year: {year}")
            for assignee_username, assigned_username in assignments_for_year.items():
                print(f"  - Attempting to assign '{assigned_username}' to '{assignee_username}'...")

                # Get assigned_user_id
                if assigned_username not in user_id_cache:
                    assigned_user = db.query(User).filter(User.username == assigned_username).first()
                    if not assigned_user:
                        print(f"    WARNING: User '{assigned_username}' not found. Skipping this assignment.")
                        continue
                    user_id_cache[assigned_username] = assigned_user.id
                assigned_user_id = user_id_cache[assigned_username]

                # Get assignee_user_id
                if assignee_username not in user_id_cache:
                    assignee_user = db.query(User).filter(User.username == assignee_username).first()
                    if not assignee_user:
                        print(f"    WARNING: User '{assignee_username}' not found. Skipping this assignment.")
                        continue
                    user_id_cache[assignee_username] = assignee_user.id
                assignee_user_id = user_id_cache[assignee_username]

                # Determine a 'created_at' date for historical data.
                # For simplicity, we'll use January 1st of the assignment year.
                assignment_created_at = datetime(year, 1, 1)

                # Create the new Assignment object
                new_assignment = Assignment(
                    year=year,
                    assigned_user_id=assigned_user_id,
                    assignee_user_id=assignee_user_id,
                    created_at=assignment_created_at
                )

                db.add(new_assignment)
                print(f"    Added assignment: Year={year}, AssignedUserID={assigned_user_id} (for {assigned_username}), AssigneeUserID={assignee_user_id} (for {assignee_username})")

        db.commit()
        print("\nAll historical assignments added successfully!")

    except IntegrityError as e:
        db.rollback()
        print(f"\nERROR: Database integrity error occurred. Rolling back changes. Error: {e}")
        print("This often happens if you try to insert duplicate data or violate a constraint.")
    except Exception as e:
        if db:
            db.rollback()
        print(f"\nERROR: An unexpected error occurred. Rolling back changes. Error: {e}")
    finally:
        if db:
            db.close()
            print("Database session closed.")


# --- Example Usage ---
if __name__ == "__main__":
    # Ensure the database file exists and tables are created before attempting to add data
    init_db_if_not_exists()

    # --- IMPORTANT: You need to have users with these usernames already in your 'users' table ---
    # For demonstration, let's assume 'd-dawg', 'brinkle', and 'cole' exist.
    # If they don't, the script will print warnings and skip those assignments.

    # Sample historical assignment data
    historical_assignments_data = {
        2022: {
            'd-dawg': 'brinkle',
            'brinkle': 'teej',
            'teej': 'd-dawg'
        },
        2021: {
            'd-dawg': 'brinkle',
            'brinkle': 'teej',
            'teej': 'd-dawg'
        },
        2020: {
            'd-dawg': 'teej',
            'brinkle': 'd-dawg',
            'teej': 'brinkle'
        }
    }

    add_historical_assignments(historical_assignments_data)

    # Optional: Verify data by querying the assignments table
    print("\nVerifying assignments in the database:")
    db_session = None
    try:
        db_session = get_db_session()
        all_assignments = db_session.query(Assignment).all()
        for assignment in all_assignments:
            # For better readability, fetch usernames for assigned_user_id and assignee_user_id
            assigned_user = db_session.query(User).get(assignment.assigned_user_id)
            assignee_user = db_session.query(User).get(assignment.assignee_user_id)
            
            print(f"  ID: {assignment.id}, Year: {assignment.year}, "
                  f"Assigned: {assigned_user.username if assigned_user else 'N/A'} (ID: {assignment.assigned_user_id}), "
                  f"Assignee: {assignee_user.username if assignee_user else 'N/A'} (ID: {assignment.assignee_user_id}), "
                  f"Created At: {assignment.created_at}")
    except Exception as e:
        print(f"Error during verification: {e}")
    finally:
        if db_session:
            db_session.close()
            print("Verification session closed.")

