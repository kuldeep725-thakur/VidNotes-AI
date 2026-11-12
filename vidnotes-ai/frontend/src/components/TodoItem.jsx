import { CalendarDays, Check, Pencil, PlayCircle, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { formatDueDate, isOverdue } from '../utils/format.js';
import TodoFields, { toFormValues, toPayload } from './TodoFields.jsx';

export default function TodoItem({ todo, index = 0, videos, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState(() => toFormValues(todo));
  const [busy, setBusy] = useState(false);

  async function run(action) {
    setBusy(true);
    try {
      return await action();
    } finally {
      setBusy(false);
    }
  }

  async function save(event) {
    event.preventDefault();
    if (!values.title.trim()) return;
    const saved = await run(() => onUpdate(todo.id, toPayload(values)));
    if (saved) setEditing(false);
  }

  function startEditing() {
    setValues(toFormValues(todo));
    setEditing(true);
  }

  if (editing) {
    return (
      <li className="todo-item editing">
        <form className="todo-edit" onSubmit={save}>
          <TodoFields values={values} onChange={setValues} videos={videos} idPrefix={`edit-${todo.id}`} autoFocus />
          <div className="todo-edit-actions">
            <button type="button" className="btn btn-sm btn-ghost" onClick={() => setEditing(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-sm btn-primary" disabled={busy || !values.title.trim()}>
              Save
            </button>
          </div>
        </form>
      </li>
    );
  }

  const overdue = todo.due_date && !todo.is_done && isOverdue(todo.due_date);

  return (
    <li className={`todo-item${todo.is_done ? ' done' : ''}`} style={{ '--i': index }}>
      <button
        type="button"
        className="todo-check"
        role="checkbox"
        aria-checked={todo.is_done}
        aria-label={todo.is_done ? `Mark "${todo.title}" as not done` : `Mark "${todo.title}" as done`}
        onClick={() => run(() => onUpdate(todo.id, { is_done: !todo.is_done }))}
        disabled={busy}
      >
        {todo.is_done && <Check size={13} />}
      </button>

      <div className="todo-body">
        <p className="todo-title">{todo.title}</p>
        {(todo.due_date || todo.video_id) && (
          <p className="todo-meta">
            {todo.due_date && (
              <span className={overdue ? 'overdue' : ''}>
                <CalendarDays size={13} />
                {overdue ? 'Overdue · ' : 'Due '}
                {formatDueDate(todo.due_date)}
              </span>
            )}
            {todo.video_id && (
              <Link to={`/notes/${todo.video_id}`}>
                <PlayCircle size={13} />
                {todo.video_title}
              </Link>
            )}
          </p>
        )}
      </div>

      <div className="todo-actions">
        <button
          type="button"
          className="btn btn-ghost btn-icon"
          onClick={startEditing}
          aria-label={`Edit "${todo.title}"`}
        >
          <Pencil size={15} />
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-icon todo-delete"
          onClick={() => run(() => onDelete(todo))}
          disabled={busy}
          aria-label={`Delete "${todo.title}"`}
        >
          <Trash2 size={15} />
        </button>
      </div>
    </li>
  );
}
