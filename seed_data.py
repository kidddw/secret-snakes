"""
Seed the local SQLite database with realistic test data for development.

Creates an admin user, several members, two years of historical assignments,
and a batch of tips so every page (home, profile, assignment, give-tips, admin)
renders with real content.

Usage (from the project root, with your virtualenv active):

    python seed_data.py            # seed only if the DB has no users
    python seed_data.py --force    # wipe existing data first, then seed

The target database is whatever app.database resolves, i.e. the
SQLITE_DATABASE_FILEPATH env var, or ./database.db by default. This script is
intended for LOCAL TESTING ONLY — do not run it against production data.
"""

import os
import sys
import argparse
import datetime

# app.auth refuses to import without these set (security fail-fast). Provide
# throwaway values so the seeder can reuse the app's password hashing. These do
# not need to match production and are never used to sign anything here.
os.environ.setdefault("SECRET_KEY", "seed-script-secret-not-for-production")
os.environ.setdefault("SESSION_SECRET_KEY", "seed-script-session-not-for-production")

from app import models, database, auth  # noqa: E402

CURRENT_YEAR = datetime.datetime.now().year
# The "active" year shown across the app. We populate this one fully (assignments
# + tips) and leave CURRENT_YEAR open so the admin "create assignments" flow is
# also testable.
ACTIVE_YEAR = CURRENT_YEAR - 1
PRIOR_YEAR = CURRENT_YEAR - 2

DEFAULT_PASSWORD = "password123"
ADMIN_PASSWORD = "admin12345"

# (username, first, last, email, is_admin, street, unit, city, state, zip)
MEMBERS = [
    ("admin",    "Daniel",   "Kidd",      "admin@example.com",    True,  "100 Cypress Ln",   None,      "Nashville",   "TN", "37011"),
    ("vipers",   "Vanessa",  "Pearson",   "vanessa@example.com",  False, "22 Garden St",     "Apt 4B",  "Austin",      "TX", "73301"),
    ("cobraco",  "Carlos",   "Obregon",   "carlos@example.com",   False, "871 Mojave Rd",    None,      "Phoenix",     "AZ", "85001"),
    ("pythonp",  "Priya",    "Patel",     "priya@example.com",    False, "5 Birch Court",    "Unit 12", "Portland",    "OR", "97035"),
    ("mamba8",   "Marcus",   "Bell",      "marcus@example.com",   False, "44 Lakeshore Dr",  None,      "Chicago",     "IL", "60601"),
    ("ssly",     "Sara",     "Lyles",     "sara@example.com",     False, "309 Elm Avenue",   "Apt 2",   "Denver",      "CO", "80014"),
    ("kingsnake","Kenji",    "Sato",      "kenji@example.com",    False, "777 Harbor Blvd",  None,      "Seattle",     "WA", "98101"),
    ("adderall", "Adaeze",   "Okafor",    "adaeze@example.com",   False, "18 Magnolia Way",  None,      "Atlanta",     "GA", "30301"),
]

# Tips for the ACTIVE_YEAR: (subject_username, contributor_username, content)
TIPS = [
    ("vipers",   "cobraco",  "She's been eyeing a cast-iron skillet set all year."),
    ("vipers",   "pythonp",  "Loves anything with eucalyptus — candles, soaps, the works."),
    ("cobraco",  "mamba8",   "Big into desert hiking. A good water filter would land well."),
    ("pythonp",  "ssly",     "Collects enamel pins. Bonus points for snake-themed ones."),
    ("mamba8",   "kingsnake","Vinyl guy. He's missing 'Rumours' from his collection."),
    ("ssly",     "adderall", "Tea over coffee. A nice loose-leaf sampler would be perfect."),
    ("kingsnake","admin",    "Just got into bouldering — chalk bag or grip trainer."),
    ("adderall", "vipers",   "Always cold at her desk. A heated blanket would be clutch."),
    ("vipers",   "admin",    "Reminder: she already has the green mug, don't re-gift it!"),
]


def make_derangement(ids, shift):
    """Return {giver_id: receiver_id} where no one gets themselves (cyclic shift)."""
    n = len(ids)
    shift = shift % n or 1
    return {ids[i]: ids[(i + shift) % n] for i in range(n)}


def wipe(db):
    """Delete all rows from the app tables (local testing only)."""
    for model in (models.Tip, models.Assignment, models.AssignmentExclusion,
                  models.Config, models.User):
        db.query(model).delete()
    db.commit()


def seed(db):
    now = datetime.datetime.utcnow()

    # --- Users -----------------------------------------------------------
    users_by_username = {}
    for (username, first, last, email, is_admin,
         street, unit, city, state, zipcode) in MEMBERS:
        password = ADMIN_PASSWORD if is_admin else DEFAULT_PASSWORD
        user = models.User(
            username=username,
            hashed_password=auth.get_password_hash(password),
            email=email,
            is_admin=is_admin,
            created_at=now,
            first_name=first,
            last_name=last,
            shipping_street_address=street,
            shipping_unit=unit,
            shipping_city=city,
            shipping_zipcode=zipcode,
            shipping_state=state,
        )
        db.add(user)
        users_by_username[username] = user
    db.commit()

    ids = [users_by_username[m[0]].id for m in MEMBERS]

    # --- Config ----------------------------------------------------------
    db.add(models.Config(key="assignment_year", value=str(ACTIVE_YEAR),
                         start_time=now, end_time=None))
    db.add(models.Config(key="allow_registration", value="True",
                         start_time=now, end_time=None))
    db.commit()

    # --- Assignments (two years, different cycles) -----------------------
    for year, shift in ((PRIOR_YEAR, 1), (ACTIVE_YEAR, 2)):
        for giver_id, receiver_id in make_derangement(ids, shift).items():
            db.add(models.Assignment(
                assignee_user_id=giver_id,
                assigned_user_id=receiver_id,
                year=year,
                created_at=now,
            ))
    db.commit()

    # --- Tips (for the active year) --------------------------------------
    for offset, (subject_un, contributor_un, content) in enumerate(TIPS):
        db.add(models.Tip(
            content=content,
            year=ACTIVE_YEAR,
            subject_user_id=users_by_username[subject_un].id,
            contributor_user_id=users_by_username[contributor_un].id,
            created_at=now - datetime.timedelta(days=offset),
        ))
    db.commit()


def main():
    parser = argparse.ArgumentParser(description="Seed local test data.")
    parser.add_argument("--force", action="store_true",
                        help="Wipe existing data before seeding.")
    args = parser.parse_args()

    print(f"Target database: {database.SQLALCHEMY_DATABASE_URL}")
    database.init_db()

    db = database.SessionLocal()
    try:
        existing = db.query(models.User).count()
        if existing and not args.force:
            print(f"\nDatabase already contains {existing} user(s).")
            print("Refusing to modify it. Re-run with --force to wipe and reseed.")
            sys.exit(1)

        if args.force and existing:
            print("--force: wiping existing data...")
            wipe(db)

        seed(db)

        n_users = db.query(models.User).count()
        n_assign = db.query(models.Assignment).count()
        n_tips = db.query(models.Tip).count()
    finally:
        db.close()

    print("\nSeed complete:")
    print(f"  users:       {n_users}")
    print(f"  assignments: {n_assign}  (years {PRIOR_YEAR} & {ACTIVE_YEAR})")
    print(f"  tips:        {n_tips}  (year {ACTIVE_YEAR})")
    print(f"  active assignment_year: {ACTIVE_YEAR}  ({CURRENT_YEAR} left open for testing)")
    print("\nLog in with:")
    print(f"  admin  -> username: admin     password: {ADMIN_PASSWORD}   (admin panel)")
    print(f"  member -> username: vipers    password: {DEFAULT_PASSWORD}")
    print("  (all non-admin members share the same password)")


if __name__ == "__main__":
    main()
