from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import crud, models
from app.database.connection import get_db
from app.database.schemas import PasswordChange, TokenResponse, UserCreate, UserLogin, UserOut, UserUpdate
from app.dependencies import get_current_user
from app.services.auth_service import create_access_token, hash_password, verify_password
from app.utils.errors import AppError

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _token_response(user: models.User) -> TokenResponse:
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> TokenResponse:
    if crud.get_user_by_email(db, payload.email):
        raise AppError("An account with this email already exists.", status_code=409)
    user = crud.create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        preferred_language=payload.preferred_language,
        organization=payload.organization,
        is_admin=payload.email.lower() in settings.admin_emails,
    )
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = crud.get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise AppError("Incorrect email or password.", status_code=401)
    # Admin rights follow the ADMIN_EMAILS configuration.
    should_be_admin = user.email in settings.admin_emails
    if should_be_admin and not user.is_admin:
        user.is_admin = True
        db.commit()
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: models.User = Depends(get_current_user)) -> models.User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> models.User:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: PasswordChange, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    if not verify_password(payload.current_password, user.hashed_password):
        raise AppError("Current password is incorrect.", status_code=400)
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
