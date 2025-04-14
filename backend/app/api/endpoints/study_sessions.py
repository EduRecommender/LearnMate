from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ...database import get_db
from ... import crud
from ...schemas.study_session import (
    StudySession,
    StudySessionCreate,
    StudySessionUpdate,
    Resource,
    ResourceCreate
)

router = APIRouter()

@router.post("/", response_model=StudySession, status_code=status.HTTP_201_CREATED)
def create_study_session(
    session: StudySessionCreate,
    user_id: str,
    db: Session = Depends(get_db)
):
    """Create a new study session."""
    return crud.create_study_session(db=db, user_id=user_id, session_data=session.dict())

@router.get("/", response_model=List[StudySession])
def get_study_sessions(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all study sessions for a user."""
    sessions = crud.get_user_study_sessions(db=db, user_id=user_id)
    return sessions[skip:skip + limit]

@router.get("/{session_id}", response_model=StudySession)
def get_study_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get a study session by ID."""
    db_session = crud.get_study_session(db=db, session_id=session_id)
    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    return db_session

@router.put("/{session_id}", response_model=StudySession)
def update_study_session(
    session_id: str,
    session: StudySessionUpdate,
    db: Session = Depends(get_db)
):
    """Update a study session."""
    db_session = crud.update_study_session(
        db=db,
        session_id=session_id,
        session_data=session.dict(exclude_unset=True)
    )
    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    return db_session

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Delete a study session."""
    success = crud.delete_study_session(db=db, session_id=session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )

@router.post("/{session_id}/resources", response_model=Resource, status_code=status.HTTP_201_CREATED)
def create_resource(
    session_id: str,
    resource: ResourceCreate,
    db: Session = Depends(get_db)
):
    """Create a new resource for a study session."""
    db_session = crud.get_study_session(db=db, session_id=session_id)
    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    return crud.create_resource(db=db, session_id=session_id, resource_data=resource.dict())

@router.get("/{session_id}/resources", response_model=List[Resource])
def get_session_resources(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get all resources for a study session."""
    db_session = crud.get_study_session(db=db, session_id=session_id)
    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )
    return crud.get_session_resources(db=db, session_id=session_id)

@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db)
):
    """Delete a resource."""
    success = crud.delete_resource(db=db, resource_id=resource_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )