"""FastAPI backend for Noteflow notes application.

This application provides RESTful APIs for user registration, authentication (JWT),
and CRUD operations for notes. Integrates with the notes_database container using SQLAlchemy models.

Environment variable required:
    NOTEFLOW_DATABASE_URL - The database URL for connecting to the notes database.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os

# Import SQLAlchemy Base and models from notes_database container
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../notes_database"))
from models import User, Note

# SECRET KEY for JWT (in real deployments, read this from .env securely!)
SECRET_KEY = os.environ.get("NOTEFLOW_SECRET_KEY", "CHANGEME_SUPERSECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = os.environ.get(
    "NOTEFLOW_DATABASE_URL",
    "sqlite:///../../notes_database/test.db"
)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Pydantic Schemas ---


class UserCreate(BaseModel):
    username: str = Field(..., description="Username for registration", min_length=3, max_length=50)
    password: str = Field(..., description="Password", min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class NoteCreate(BaseModel):
    title: str = Field(..., description="Note title", min_length=1, max_length=100)
    content: Optional[str] = Field(None, description="Note content")


class NoteOut(BaseModel):
    id: int
    title: str
    content: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title")
    content: Optional[str] = Field(None, description="Updated content")


# --- Utility functions ---

def get_db():
    """Provide a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    """Verify password using passlib."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Hash password using passlib."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# --- Dependency for current user (JWT auth) ---

# PUBLIC_INTERFACE
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get the currently authenticated user from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user


# --- FastAPI App setup ---

app = FastAPI(
    title="Noteflow Notes API",
    description="Backend API for Noteflow: CRUD notes and user authentication.",
    version="1.0.0",
    openapi_tags=[
        {"name": "auth", "description": "User Authentication"},
        {"name": "notes", "description": "Notes CRUD operations"},
        {"name": "users", "description": "User management"},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---

@app.get("/", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


# --- Authentication & User ---

# PUBLIC_INTERFACE
@app.post("/auth/register", response_model=UserOut, tags=["auth"], summary="Register a new user")
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with a unique username.

    - **username**: The desired username.
    - **password**: The desired password.
    """
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user = User(username=user.username, hashed_password=get_password_hash(user.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/auth/login", response_model=Token, tags=["auth"], summary="Login user and get JWT token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT access token.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/logout", tags=["auth"], summary="Logout user")
def logout(response: Response):
    """
    Client-side JWT/auth should discard the token. Returns a message suggesting front-end remove credentials.
    """
    response.delete_cookie(key="Authorization")
    return {"message": "Logout successful. Remove your access token on the client."}


@app.get("/users/me", response_model=UserOut, tags=["users"], summary="Get current user info")
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get user info for the current authenticated user.
    """
    return current_user


# --- Notes CRUD Endpoints ---

# PUBLIC_INTERFACE
@app.post("/notes/", response_model=NoteOut, tags=["notes"], summary="Create note", status_code=201)
def create_note(note: NoteCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create a note belonging to the currently authenticated user.
    """
    db_note = Note(title=note.title, content=note.content, user_id=current_user.id)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


# PUBLIC_INTERFACE
@app.get("/notes/", response_model=List[NoteOut], tags=["notes"], summary="List my notes")
def list_notes(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    List all notes for the current user.
    """
    notes = db.query(Note).filter(Note.user_id == current_user.id).offset(skip).limit(limit).all()
    return notes


# PUBLIC_INTERFACE
@app.get("/notes/{note_id}", response_model=NoteOut, tags=["notes"], summary="Get note by ID")
def get_note(note_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieve a note belonging to the current user by note ID.
    """
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


# PUBLIC_INTERFACE
@app.put("/notes/{note_id}", response_model=NoteOut, tags=["notes"], summary="Update note")
def update_note(note_id: int, note_update: NoteUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update properties of an existing note by ID (owned by the current user).
    """
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    if note_update.title is not None:
        note.title = note_update.title
    if note_update.content is not None:
        note.content = note_update.content
    note.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(note)
    return note


# PUBLIC_INTERFACE
@app.delete("/notes/{note_id}", status_code=204, tags=["notes"], summary="Delete note")
def delete_note(note_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Delete a note by note ID if it belongs to the current user.
    """
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- OpenAPI Doc Customization for WebSocket Example ---
@app.get("/docs/ws-auth-notes", tags=["auth"], summary="WebSocket usage in project (N/A)", include_in_schema=True)
def ws_example():
    """
    This project does **not** use WebSockets; all traffic is via REST endpoints.
    """
    return {"message": "This API supports RESTful HTTP only. No WebSocket endpoints are present."}
