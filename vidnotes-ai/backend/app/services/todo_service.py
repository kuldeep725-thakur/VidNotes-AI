"""Database operations for study to-do items."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models import Todo, Video
from app.schemas.todo import TodoCreate, TodoFilter, TodoOut, TodoUpdate


def to_out(todo: Todo) -> TodoOut:
    return TodoOut(
        id=todo.id,
        title=todo.title,
        is_done=todo.is_done,
        due_date=todo.due_date,
        video_id=todo.video_id,
        video_title=todo.video.title if todo.video else None,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
    )


def list_todos(db: Session, user_id: str, status: TodoFilter) -> list[Todo]:
    # Open tasks first, then by due date (tasks without one last), newest first.
    query = select(Todo).where(Todo.user_id == user_id).options(selectinload(Todo.video)).order_by(
        Todo.is_done, Todo.due_date.is_(None), Todo.due_date, Todo.created_at.desc()
    )
    if status != "all":
        query = query.where(Todo.is_done == (status == "done"))
    return list(db.scalars(query))


def get_todo(db: Session, user_id: str, todo_id: int) -> Todo:
    query = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id).options(selectinload(Todo.video))
    todo = db.scalar(query)
    if todo is None:
        raise AppError("Task not found. It may have been deleted.", 404)
    return todo


def create_todo(db: Session, user_id: str, data: TodoCreate) -> Todo:
    _check_video_exists(db, user_id, data.video_id)
    todo = Todo(user_id=user_id, **data.model_dump())
    db.add(todo)
    db.commit()
    return get_todo(db, user_id, todo.id)


def update_todo(db: Session, user_id: str, todo_id: int, data: TodoUpdate) -> Todo:
    todo = get_todo(db, user_id, todo_id)
    changes = data.model_dump(exclude_unset=True)
    for required_field in ("title", "is_done"):
        if required_field in changes and changes[required_field] is None:
            raise AppError(f"{required_field} cannot be empty.", 422)
    if "video_id" in changes:
        _check_video_exists(db, user_id, changes["video_id"])

    for field, value in changes.items():
        setattr(todo, field, value)
    db.commit()
    db.expire(todo, ["video"])
    return get_todo(db, user_id, todo_id)


def delete_todo(db: Session, user_id: str, todo_id: int) -> None:
    db.delete(get_todo(db, user_id, todo_id))
    db.commit()


def _check_video_exists(db: Session, user_id: str, video_id: int | None) -> None:
    """A task may only link to one of the user's own videos."""
    if video_id is None:
        return
    owned = db.scalar(select(Video.id).where(Video.id == video_id, Video.user_id == user_id))
    if owned is None:
        raise AppError("The linked video does not exist.", 422)
