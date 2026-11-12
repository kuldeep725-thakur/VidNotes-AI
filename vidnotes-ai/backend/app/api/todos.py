from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.auth import CurrentUser, get_current_user
from app.schemas.todo import TodoCreate, TodoFilter, TodoOut, TodoUpdate
from app.services import todo_service

router = APIRouter(prefix="/api/todos", tags=["todos"])


@router.get("", response_model=list[TodoOut])
def list_todos(
    status_filter: TodoFilter = Query(default="all", alias="status"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [todo_service.to_out(todo) for todo in todo_service.list_todos(db, user.id, status_filter)]


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return todo_service.to_out(todo_service.create_todo(db, user.id, payload))


@router.get("/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return todo_service.to_out(todo_service.get_todo(db, user.id, todo_id))


@router.patch("/{todo_id}", response_model=TodoOut)
def update_todo(
    todo_id: int, payload: TodoUpdate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    return todo_service.to_out(todo_service.update_todo(db, user.id, todo_id, payload))


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    todo_service.delete_todo(db, user.id, todo_id)
