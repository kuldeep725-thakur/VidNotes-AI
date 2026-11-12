// All requests go to the FastAPI backend. In development Vite proxies /api.
// No API keys live in frontend code: the backend holds them.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

// Set by the auth context once the user signs in.
let getAccessToken = async () => null;
let onUnauthorized = () => {};

export function configureAuth({ tokenProvider, unauthorizedHandler }) {
  getAccessToken = tokenProvider;
  onUnauthorized = unauthorizedHandler;
}

async function send(path, options = {}) {
  const token = await getAccessToken();
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error('Cannot reach the VidNotes server. Make sure the backend is running.');
  }
  if (response.status === 401 && token) onUnauthorized();
  return response;
}

async function errorFrom(response) {
  const data = await response.json().catch(() => null);
  const error = new Error(data?.detail || `Request failed (${response.status}).`);
  error.status = response.status;
  return error;
}

async function request(path, options = {}) {
  const response = await send(path, options);
  if (!response.ok) throw await errorFrom(response);
  if (response.status === 204) return null;
  return response.json().catch(() => null);
}

export function getPublicConfig() {
  return request('/api/config');
}

export function analyzeVideo(url, quizCount) {
  return request('/api/videos', {
    method: 'POST',
    body: JSON.stringify({ url, quiz_count: quizCount }),
  });
}

export function listVideos(search = '') {
  const query = search ? `?search=${encodeURIComponent(search)}` : '';
  return request(`/api/videos${query}`);
}

export function getVideo(id) {
  return request(`/api/videos/${id}`);
}

export function getVideoStatus(id) {
  return request(`/api/videos/${id}/status`);
}

export function deleteVideo(id) {
  return request(`/api/videos/${id}`, { method: 'DELETE' });
}

// The PDF needs the sign-in token, so it is fetched and then saved as a file.
export async function downloadPdf(id, language) {
  const response = await send(`/api/videos/${id}/pdf?language=${language}`);
  if (!response.ok) throw await errorFrom(response);
  const disposition = response.headers.get('Content-Disposition') ?? '';
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? `vidnotes-${language}.pdf`;
  const url = URL.createObjectURL(await response.blob());
  const link = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function listQuizResults(videoId) {
  return request(`/api/videos/${videoId}/quiz-results`);
}

export function saveQuizResult(videoId, language, answers) {
  return request(`/api/videos/${videoId}/quiz-results`, {
    method: 'POST',
    body: JSON.stringify({ language, answers }),
  });
}

export function listTodos(status = 'all') {
  return request(`/api/todos?status=${status}`);
}

export function createTodo(todo) {
  return request('/api/todos', { method: 'POST', body: JSON.stringify(todo) });
}

// Only the fields passed in `changes` are updated; null clears a field.
export function updateTodo(id, changes) {
  return request(`/api/todos/${id}`, { method: 'PATCH', body: JSON.stringify(changes) });
}

export function deleteTodo(id) {
  return request(`/api/todos/${id}`, { method: 'DELETE' });
}

export function getProfile() {
  return request('/api/me');
}

export function updateProfile(fullName) {
  return request('/api/me', { method: 'PATCH', body: JSON.stringify({ full_name: fullName }) });
}

export function getPreferences() {
  return request('/api/me/preferences');
}

export function updatePreferences(changes) {
  return request('/api/me/preferences', { method: 'PATCH', body: JSON.stringify(changes) });
}
