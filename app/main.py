from typing import List
import datetime
from distutils.util import strtobool
from fastapi import FastAPI, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
import logging

from app import models, schemas, auth, database, config, snake_assignments, tips


# Adding logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Add email configuration (place in config)  # todo
conf = None
# conf = ConnectionConfig(
#     MAIL_USERNAME="your@email.com",
#     MAIL_PASSWORD="your_email_password",
#     MAIL_FROM="noreply@secretsanta.com",
#     MAIL_PORT=587,
#     MAIL_SERVER="smtp.your-email-provider.com",
#     MAIL_TLS=True,
#     MAIL_SSL=False
# )


# Initialize app
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Session Configuration
app.add_middleware(SessionMiddleware, secret_key="livsoig7se8igw4ivufsd89h")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup_event():
    """Initialize the database when the app starts."""
    database.init_db()
    config.initialize_config(next(database.get_db()))


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    db: Session = Depends(database.get_db)
):
    """Home page."""

    # If registration is not allowed, redirect to login page
    unauthenticated_response = templates.TemplateResponse(
        "home.html",
        {"request": request, "user_authenticated": False}
    )

    # Check for session token
    access_token = request.session.get("access_token")

    # If authentication token not available, display home page with user is authenticated set to false
    if not access_token:
        return unauthenticated_response

    # Get current user and generate context for template response
    current_user = auth.get_current_user(db, access_token)

    # If authentication token not valid, display home page with user is authenticated set to false
    if not current_user:
        return unauthenticated_response

    # If authentication token in session and valid, display home page with user is authenticated set to true
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "user_authenticated": True, "allow_registration": allow_registration}
    )


@app.get("/home", response_class=HTMLResponse)
async def home(
    request: Request, 
    db: Session = Depends(database.get_db)
): 
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/check-registration-status")
async def check_registration_status(
    db: Session = Depends(database.get_db)
):
    
    # Check if registration is allowed
    allow_registration = config.get_config(db).get("allow_registration", "True")
    allow_registration = (allow_registration == "True")

    print('CHECKING REGISTRATION STATUS', allow_registration, type(allow_registration))

    return {"allow_registration": allow_registration}


@app.get("/register")
async def register_page(
    request: Request,
    db: Session = Depends(database.get_db)
):
    """Rendering the register page"""

    # Check if registration is allowed
    auth.get_allowed_registration()

    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    shipping_street_address: str = Form(...),
    shipping_unit: str = Form(None),  # This field is optional
    shipping_city: str = Form(...),
    shipping_zipcode: str = Form(...),
    shipping_state: str = Form(...),
    db: Session = Depends(database.get_db)
):
    """Register a new user."""

    # Check if registration is allowed
    auth.get_allowed_registration()

    # Query for this username in the users table
    db_user = db.query(models.User).filter(models.User.username == username).first()

    # If this username is already found in the users table then raise an exception
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Get hashed password from provided password
    # We will store this version of the password
    hashed_password = auth.get_password_hash(password)

    # Initialize User table-object instance using the provided details and the hashed password
    new_user = models.User(
        username=username,
        hashed_password=hashed_password,
        email=email,
        is_admin=False,
        created_at=datetime.datetime.now(),
        first_name=first_name,
        last_name=last_name,
        shipping_street_address=shipping_street_address,
        shipping_unit=shipping_unit,
        shipping_city=shipping_city,
        shipping_zipcode=shipping_zipcode,
        shipping_state=shipping_state
    )

    logger.info(f"Register attempt for user: {new_user.username}")

    # Add new row to the users table for this new user
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RedirectResponse(url="/", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""

    # Check for session token
    access_token = request.session.get("access_token")

    # If authentication token in session, display home page with user is authenticated set to true
    user_authenticated = bool(access_token)

    # Return template
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "user_authenticated": user_authenticated}
    )


@app.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    """Login as a user."""

    logger.info(f"Login attempt for user: {form_data.username}")

    # Check if user exists
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create an authentication token
    access_token = auth.create_access_token(data={"sub": user.username})
    logger.info(f"Token generated: {access_token}")

    # Store the token in the session
    request.session["access_token"] = access_token

    return RedirectResponse(url="/profile", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    logger.info(f"Logout attempt")

    # Remove the token from the session
    request.session.pop("access_token", None)

    return RedirectResponse(url="/", status_code=302)


@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """
    Authenticate user.
    If able to be authenticated, provide an access token

    """

    # From the standard OAuthPasswordRequestForm, pull username and password and authenticate the claimed user
    user: schemas.User = auth.authenticate_user(db, form_data.username, form_data.password)

    # If no valid user returned, raise exception
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create the timedelta for how long until the token expires
    access_token_expires = datetime.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Create an access token, providing a payload containing the username and an expiration timedelta
    access_token = auth.create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_form(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@app.post("/forgot-password")
async def forgot_password(
        request: Request,
        email: str = Form(...),
        db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:

        # Create access token for reset
        reset_token = auth.create_access_token(
            data={"sub": user.username},
            expires_delta=datetime.timedelta(minutes=15)
        )

        # Store token in database
        user.reset_token = reset_token
        user.reset_token_expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        db.commit()

        # Send email (implementation example)
        reset_link = f"http://yourdomain.com/reset-password?token={reset_token}"  #todo
        message = MessageSchema(
            subject="Password Reset Request",
            recipients=[email],
            body=f"Click to reset: {reset_link}",
            subtype="html"
        )
        fm = FastMail(conf)
        await fm.send_message(message)

    return templates.TemplateResponse("reset_instructions_sent.html", {"request": request})


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    return templates.TemplateResponse("forgot_password.html", {"request": request, "token": token})


@app.post("/reset-password")
async def reset_password(
        request: Request,
        access_token: str = Form(...),
        new_password: str = Form(...),
        db: Session = Depends(database.get_db)
):
    try:

        # Determine user from access token
        user = auth.get_user_for_reset(db, access_token)

        # If no valid user returned, raise exception
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user.hashed_password = auth.get_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.commit()
        return RedirectResponse(url="/", status_code=303)

    except Exception as e:
        pass

    return templates.TemplateResponse("forgot_password.html", {
        "request": request,
        "error": "Invalid or expired token"
    })


@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """Check the current user and get their information."""
    return current_user


@app.get("/profile")
async def profile(
    request: Request,
    db: Session = Depends(database.get_db)
):
    """Profile page."""

    try:

        # Get the token from the session
        access_token = request.session.get("access_token")

        if not access_token:
            return RedirectResponse(url="/", status_code=302)

        # Get current user and generate context for template response
        current_user = auth.get_current_user(db, access_token)

        if not current_user:
            return RedirectResponse(url="/", status_code=302)

        # Fetch all users if admin
        all_users = db.query(models.User).all() if current_user.is_admin else []

        # Fetch user's assignments
        assignments = db.query(models.Assignment).filter(
            models.Assignment.assignee_user_id == current_user.id
        ).order_by(desc(models.Assignment.year)).all()

        # Get the latest year in the assignments table
        latest_year = db.query(func.max(models.Assignment.year)).scalar()

        # Get the current assignment year
        assignment_year = config.get_config(db)['assignment_year']
        assignment_year = int(assignment_year) if assignment_year else latest_year

        # Check if registration is allowed
        allow_registration = config.get_config(db).get("allow_registration", "True")
        allow_registration = (allow_registration == "True")

        # Get number of tips for current assignemnt
        number_of_tips = tips.count_tips_for_current_assignment(db, current_user.id, assignment_year)

        context = {
            "request": request,
            "user": current_user,
            "is_admin": current_user.is_admin,
            "all_users": all_users,
            "assignments": assignments,
            "assignment_year": assignment_year,
            "allow_registration": allow_registration,
            "number_of_tips": number_of_tips,
            "user_authenticated": True
        }
        return templates.TemplateResponse("profile.html", context)

    except HTTPException as e:
        logger.warning(f"Authentication failed: {e.detail}")
        return RedirectResponse("/login", status_code=302)

    except Exception as e:
        logger.error(f"Error during template rendering: {str(e)}")
        raise


@app.patch("/update-profile")
async def update_profile(
        request: Request,
        user_update: schemas.UserUpdate,
        db: Session = Depends(database.get_db)
):

    # Get the token from the session
    access_token = request.session.get("access_token")

    # Get current user
    current_user = auth.get_current_user(db, access_token)

    # For all fields provided, overwrite current user object's attributes
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)

    # Commit updates to database
    db.commit()
    db.refresh(current_user)
    return {"message": "Profile updated successfully"}


@app.get("/update_profile_page")
async def update_profile_page(
        request: Request,
        current_user: schemas.User = Depends(auth.get_current_user)):
    logger.info(f"Update profile page attemp. User: {current_user}")
    return templates.TemplateResponse("profile.html", {"request": request, "user": current_user})


@app.get("/users/", response_model=List[schemas.User])
def list_users(
    request: Request,
    db: Session = Depends(database.get_db),
):
    """Retrieve a list of all users. Requires admin privileges."""

    # Get the token from the session
    access_token = request.session.get("access_token")

    # Get current user and check admin
    current_user = auth.get_current_user(db, access_token)
    auth.get_current_admin_user(current_user)

    # Query users
    users = db.query(models.User).all()

    return users


@app.post("/admin/toggle-registration", response_model=dict)
def toggle_registration(
    request: Request,
    allow_registration: bool = Form(...),
    db: Session = Depends(database.get_db)
):
    """
    Allows admin to enable or disable new user registration.
    """

    # Get the token from the session
    access_token = request.session.get("access_token")

    # Get current user and check admin
    current_user = auth.get_current_user(db, access_token)
    auth.get_current_admin_user(current_user)

    # Set the configuration for registration
    config.set_config(db, "allow_registration", str(allow_registration))

    status_str = "enabled" if allow_registration else "disabled"
    return {"message": f"Registration has been {status_str}."}


@app.post("/admin/set-assignment-year")
def set_assignment_year(
        request: Request,
        assignment_year_request: schemas.AssignmentYearUpdate,
        db: Session = Depends(database.get_db)
):
    """If current user is admin, set the current assignment year."""

    # Get the token from the session
    access_token = request.session.get("access_token")

    # Get current user and generate context for template response
    current_user = auth.get_current_user(db, access_token)

    # Check if current user is admin
    auth.get_current_admin_user(current_user)

    logger.info(f"assignment_year: {assignment_year_request.assignment_year}")

    # Set assignment year
    config.set_config(db, 'assignment_year', str(assignment_year_request.assignment_year))

    return {"message": f"Assignment year set to {assignment_year_request.assignment_year} successfully"}


@app.post("/admin/assign", response_model=dict)
def create_assignments(
        request: Request,
        assignments_request: schemas.AssignmentCreate,
        db: Session = Depends(database.get_db)
):
    """If current user is admin, create assignments and record them in the database."""

    # Get the token from the session
    access_token = request.session.get("access_token")

    # Get current user and generate context for template response
    current_user = auth.get_current_user(db, access_token)

    # Check if current user is admin
    auth.get_current_admin_user(current_user)

    # Parse assignment request, create assignments, and record assignments to the database
    assignments_request_dict = assignments_request.dict()

    logger.info(f"/admin/assign assignments_request_dict: {assignments_request_dict}")

    # Check if year already exists
    year = assignments_request_dict["year"]
    existing_assignments = db.query(models.Assignment).filter(models.Assignment.year == year).all()
    if existing_assignments:
        return {"message": "Requested year already has assignments"}

    assignments = snake_assignments.assign_secret_snakes(
        db,
        assignments_request_dict["participants"],
        assignments_request_dict["year"]
    )

    # Check if we have valid assignments
    if assignments is None:
        raise HTTPException(status_code=400, detail="Unable to create valid assignments")

    return {"message": "Assignments created successfully"}


@app.get("/assignment", response_class=HTMLResponse)
async def assignment(
    request: Request,
    db: Session = Depends(database.get_db),
):
    """Assignment page for the current user's latest assignment."""

    # Get the token from the session
    access_token = request.session.get("access_token")

    if not access_token:
        return RedirectResponse(url="/", status_code=302)

    # Get current user and generate context for template response
    current_user = auth.get_current_user(db, access_token)

    if not current_user:
        return RedirectResponse(url="/", status_code=302)

    # Get the latest year in the assignments table
    latest_year = db.query(func.max(models.Assignment.year)).scalar()

    # Get the current assignment year
    assignment_year = config.get_config(db)['assignment_year']
    assignment_year = int(assignment_year) if assignment_year else latest_year

    # Get the latest assignment for the current user
    assignment = db.query(models.Assignment).filter(
        models.Assignment.assignee_user_id == current_user.id,
        models.Assignment.year == assignment_year,
    ).first()

    if not assignment:
        return templates.TemplateResponse("assignment.html", {"request": request, "assignment": None})

    # Get the user they are assigned to (assigned_user)
    assigned_user = db.query(models.User).filter(models.User.id == assignment.assigned_user_id).first()

    if not assigned_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Assigned user not found")

    # Get tips for the assigned user
    current_tips = tips.get_tips_for_subject_user(db, assigned_user.id, assignment_year)

    # # Ensure created_at is a datetime object
    # for tip in current_tips:
    #     if tip.created_at and not isinstance(tip.created_at, datetime.datetime):
    #         tip.created_at = datetime.datetime.fromisoformat(str(tip.created_at))  # Convert to datetime

    context = {
        "request": request,
        "assignment": assignment,
        "assigned_user": assigned_user,
        "current_tips": current_tips,
        "user_authenticated": True
    }

    return templates.TemplateResponse("assignment.html", context)


@app.get("/tips/create", response_class=HTMLResponse)
async def create_tip_form(
    request: Request,
    db: Session = Depends(database.get_db),
):
    """Displays a form to create a new tip for a user in the latest assignment year."""

    # Get the token from the session
    access_token = request.session.get("access_token")

    if not access_token:
        return RedirectResponse(url="/", status_code=302)

    # Get current user and generate context for template response
    current_user = auth.get_current_user(db, access_token)

    if not current_user:
        return RedirectResponse(url="/", status_code=302)

    # Get the latest year in the assignments table
    latest_year = db.query(func.max(models.Assignment.year)).scalar()

    # Get the current assignment year
    assignment_year = config.get_config(db)['assignment_year']
    assignment_year = int(assignment_year) if assignment_year else latest_year

    # Get the participants from the latest assignment year
    participants = db.query(models.User).join(
        models.Assignment,
        models.User.id == models.Assignment.assignee_user_id
    ).filter(
        models.Assignment.year == assignment_year,
        models.Assignment.assignee_user_id != current_user.id  # Exclude current user
    ).distinct().all()

    # Get the user's past tips
    past_tips = tips.get_tips_for_contributor_user(db, current_user.id, assignment_year)

    logging.info(f"past_tips: {past_tips}")

    return templates.TemplateResponse("create_tip.html", {
        "request": request,
        "participants": participants,
        "year": assignment_year,
        "past_tips": past_tips,
        "user_authenticated": True
    })


@app.post("/tips/create", response_model=dict)
async def create_tip(
    request: Request,
    subject_user_id: int = Form(...),
    content: str = Form(...),
    db: Session = Depends(database.get_db),
):
    """Creates a new tip."""

    # Get the token from the session
    access_token = request.session.get("access_token")

    # Get current user and generate context for template response
    current_user = auth.get_current_user(db, access_token)

    # Get the latest year in the assignments table
    latest_year = db.query(func.max(models.Assignment.year)).scalar()

    # Get the current assignment year
    assignment_year = config.get_config(db)['assignment_year']
    assignment_year = int(assignment_year) if assignment_year else latest_year

    # Construct the data model
    tip = schemas.TipCreate(content=content, subject_user_id=subject_user_id, year=assignment_year)

    # Create tip
    db_tip = tips.create_tip(tip, db, current_user.id)

    # return {"message": "Tip created successfully"}
    return RedirectResponse(url="/tips/create", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/tips/{tip_id}/delete")
async def delete_tip_route(
    request: Request,
    tip_id: int,
    db: Session = Depends(database.get_db),
):
    """Deletes an existing tip."""

    # Get the token from the session
    access_token = request.session.get("access_token")

    # Get current user and generate context for template response
    current_user = auth.get_current_user(db, access_token)

    try:
        tips.delete_tip(db, tip_id, current_user.id)
        return {"message": "Tip deleted successfully"}

    except HTTPException as e:
        return JSONResponse(content={"detail": e.detail}, status_code=e.status_code)


@app.post("/tips/{tip_id}/update")
async def update_tip_route(
    request: Request,
    tip_id: int,
    content: str = Form(...),
    db: Session = Depends(database.get_db),
):
    """Updates an existing tip."""

    # Get the token from the session
    access_token = request.session.get("access_token")

    # Get current user and generate context for template response
    current_user = auth.get_current_user(db, access_token)

    try:
        updated_tip = tips.update_tip(db, current_user.id, tip_id, content)
        return {"message": "Tip updated successfully", "tip": updated_tip}

    except HTTPException as e:
        return JSONResponse(content={"detail": e.detail}, status_code=e.status_code)



#
#
# @app.get("/tips/me", response_model=List[schemas.Tip])
# def read_my_tips(
#         db: Session = Depends(database.get_db),
#         current_user: models.User = Depends(auth.get_current_user)
# ):
#     """Retrieve all tips for current user."""
#     return tips.get_tips_for_user(db=db, user_id=current_user.id)
#
#

