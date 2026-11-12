// Title, due date and linked video inputs, shared by the add form and edit mode.
export const EMPTY_TODO = { title: '', due_date: '', video_id: '' };

export function toFormValues(todo) {
  return { title: todo.title, due_date: todo.due_date ?? '', video_id: todo.video_id ?? '' };
}

export function toPayload(values) {
  return {
    title: values.title.trim(),
    due_date: values.due_date || null,
    video_id: values.video_id ? Number(values.video_id) : null,
  };
}

export default function TodoFields({ values, onChange, videos, idPrefix, autoFocus = false }) {
  const update = (field) => (event) => onChange({ ...values, [field]: event.target.value });

  return (
    <div className="todo-fields">
      <label htmlFor={`${idPrefix}-title`} className="visually-hidden">
        Task
      </label>
      <input
        id={`${idPrefix}-title`}
        className="input todo-title-input"
        placeholder="What do you need to study?"
        maxLength={200}
        value={values.title}
        onChange={update('title')}
        autoFocus={autoFocus}
      />
      <label htmlFor={`${idPrefix}-due`} className="visually-hidden">
        Due date
      </label>
      <input
        id={`${idPrefix}-due`}
        className="input todo-date-input"
        type="date"
        value={values.due_date}
        onChange={update('due_date')}
      />
      <label htmlFor={`${idPrefix}-video`} className="visually-hidden">
        Linked video
      </label>
      <select
        id={`${idPrefix}-video`}
        className="input todo-video-select"
        value={values.video_id}
        onChange={update('video_id')}
      >
        <option value="">No linked video</option>
        {videos.map((video) => (
          <option key={video.id} value={video.id}>
            {video.title}
          </option>
        ))}
      </select>
    </div>
  );
}
