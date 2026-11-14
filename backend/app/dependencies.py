from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import crud, models
from app.database.connection import get_db
from app.services.auth_service import decode_access_token
from app.utils.errors import AppError

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("Authentication required.", status_code=401)
    user_id = decode_access_token(credentials.credentials)
    user = crud.get_user(db, user_id)
    if user is None:
        raise AppError("User no longer exists.", status_code=401)
    return user


def get_admin_user(user: models.User = Depends(get_current_user)) -> models.User:
    if not user.is_admin:
        raise AppError("Administrator access required.", status_code=403)
    return user
