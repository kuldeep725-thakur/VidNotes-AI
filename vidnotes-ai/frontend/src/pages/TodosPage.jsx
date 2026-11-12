import { ListTodo, Plus } from 'lucide-react';
import { useEffect, useState } from 'react';
import Notice from '../components/Notice.jsx';
import { SkeletonRows } from '../components/Skeleton.jsx';
import TodoFields, { EMPTY_TODO, toPayload } from '../components/TodoFields.jsx';
import TodoItem from '../components/TodoItem.jsx';
import { createTodo, deleteTodo, listTodos, listVideos, updateTodo } from '../services/api.js';
import '../styles/pages.css';
import '../styles/todos.css';

const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'done', label: 'Done' },
];

export default function TodosPage() {
  const [todos, setTodos] = useState(null);
  const [videos, setVideos] = useState([]);
  const [filter, setFilter] = useState('all');
  const [draft, setDraft] = useState(EMPTY_TODO);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    listTodos()
      .then(setTodos)
      .catch((err) => setError(err.message));
    // Saved videos are only needed for the optional "linked video" field.
    listVideos()
      .then(setVideos)
      .catch(() => setVideos([]));
  }, []);

  async function reload() {
    setTodos(await listTodos());
  }

  async function handleAdd(event) {
    event.preventDefault();
    if (!draft.title.trim()) {
      setError('Write a task before adding it.');
      return;
    }
    setAdding(true);
    setError('');
    try {
      await createTodo(toPayload(draft));
      setDraft(EMPTY_TODO);
      await reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  }

  async function handleUpdate(id, changes) {
    setError('');
    try {
      await updateTodo(id, changes);
      await reload();
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }

  async function handleDelete(todo) {
    if (!window.confirm(`Delete the task "${todo.title}"?`)) return;
    setError('');
    try {
      await deleteTodo(todo.id);
      setTodos((current) => current.filter((t) => t.id !== todo.id));
    } catch (err) {
      setError(err.message);
    }
  }

  const openCount = todos?.filter((t) => !t.is_done).length ?? 0;
  const doneCount = (todos?.length ?? 0) - openCount;
  const visible = todos?.filter((t) => filter === 'all' || t.is_done === (filter === 'done')) ?? [];

  return (
    <div className="container todos-page">
      <header className="page-header notes-header">
        <div>
          <h1 className="page-title">To-Do</h1>
          <p className="page-subtitle">Plan what to study next. Link tasks to saved notes.</p>
        </div>
        {todos && todos.length > 0 && (
          <p className="todo-counts">
            {openCount} open · {doneCount} done
          </p>
        )}
      </header>

      <form className="todo-add" onSubmit={handleAdd} noValidate>
        <TodoFields values={draft} onChange={setDraft} videos={videos} idPrefix="new" />
        <button type="submit" className="btn btn-primary" disabled={adding}>
          <Plus size={16} /> Add task
        </button>
      </form>

      {error && (
        <Notice variant="error" title="Something went wrong">
          {error}
        </Notice>
      )}

      {!todos && !error && <SkeletonRows count={3} label="Loading your tasks" />}

      {todos && todos.length > 0 && (
        <>
          <div className="todo-toolbar">
            <div className="segmented" role="radiogroup" aria-label="Show tasks">
              {FILTERS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={filter === option.value}
                  className={filter === option.value ? 'active' : ''}
                  onClick={() => setFilter(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {visible.length > 0 ? (
            <ul className="todo-list">
              {visible.map((todo, index) => (
                <TodoItem
                  key={todo.id}
                  todo={todo}
                  index={index}
                  videos={videos}
                  onUpdate={handleUpdate}
                  onDelete={handleDelete}
                />
              ))}
            </ul>
          ) : (
            <p className="muted todo-filter-empty">
              {filter === 'done' ? 'No completed tasks yet.' : 'Everything is done. Nice work.'}
            </p>
          )}
        </>
      )}

      {todos && todos.length === 0 && (
        <div className="empty-state">
          <ListTodo size={28} />
          <h2>No tasks yet</h2>
          <p>Add what you want to revise, practise or watch next.</p>
        </div>
      )}
    </div>
  );
}
