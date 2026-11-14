from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import crud, models
from app.database.connection import get_db
from app.database.schemas import ChatRequest, ChatResponse, ChatSessionDetail, ChatSessionOut, FeedbackCreate
from app.dependencies import get_current_user
from app.services import chat_service
from app.utils.errors import NotFoundError

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse)
def send_message(payload: ChatRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> ChatResponse:
    return chat_service.handle_message(db, user, payload)


@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.list_user_sessions(db, user.id)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_session(session_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = crud.get_user_session(db, user.id, session_id, with_messages=True)
    if session is None:
        raise NotFoundError("Conversation not found.")
    return session


@router.patch("/sessions/{session_id}", response_model=ChatSessionOut)
def rename_session(session_id: int, payload: dict, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = crud.get_user_session(db, user.id, session_id)
    if session is None:
        raise NotFoundError("Conversation not found.")
    title = str(payload.get("title", "")).strip()[:255]
    if title:
        session.title = title
        db.commit()
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    session = crud.get_user_session(db, user.id, session_id)
    if session is None:
        raise NotFoundError("Conversation not found.")
    db.delete(session)
    db.commit()


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def feedback(payload: FeedbackCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if crud.get_user_message(db, user.id, payload.message_id) is None:
        raise NotFoundError("Message not found.")
    fb = crud.upsert_feedback(db, user.id, payload.message_id, payload.rating, payload.comments)
    return {"id": fb.id, "rating": fb.rating}
