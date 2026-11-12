from app.models import LOCAL_USER_ID, Video, VideoStatus


def add_video(db, youtube_id="aircAruvnKk", status=VideoStatus.COMPLETED, user_id=LOCAL_USER_ID) -> int:
    video = Video(user_id=user_id, youtube_id=youtube_id, url=f"https://www.youtube.com/watch?v={youtube_id}",
                  title="Neural nets", status=status)
    db.add(video)
    db.commit()
    return video.id


def test_create_and_get(client):
    response = client.post("/api/todos", json={"title": "  Revise chapter 1  ", "due_date": "2026-12-01"})
    assert response.status_code == 201
    todo = response.json()
    assert todo["title"] == "Revise chapter 1"
    assert todo["is_done"] is False
    assert todo["due_date"] == "2026-12-01"
    assert todo["video_id"] is None

    assert client.get(f"/api/todos/{todo['id']}").json() == todo


def test_validation(client):
    assert client.post("/api/todos", json={"title": "   "}).status_code == 422
    assert client.post("/api/todos", json={"title": "x" * 201}).status_code == 422
    assert client.post("/api/todos", json={"title": "ok", "due_date": "not-a-date"}).status_code == 422
    assert client.post("/api/todos", json={"title": "ok", "video_id": 999}).status_code == 422
    assert client.get("/api/todos?status=unknown").status_code == 422


def test_list_filters_and_order(client):
    first = client.post("/api/todos", json={"title": "Later", "due_date": "2026-12-20"}).json()
    client.post("/api/todos", json={"title": "No date"})
    client.post("/api/todos", json={"title": "Sooner", "due_date": "2026-12-01"})
    client.patch(f"/api/todos/{first['id']}", json={"is_done": True})

    assert [t["title"] for t in client.get("/api/todos").json()] == ["Sooner", "No date", "Later"]
    assert [t["title"] for t in client.get("/api/todos?status=active").json()] == ["Sooner", "No date"]
    assert [t["title"] for t in client.get("/api/todos?status=done").json()] == ["Later"]


def test_partial_update_and_clearing_fields(client):
    todo = client.post("/api/todos", json={"title": "Read", "due_date": "2026-12-01"}).json()

    updated = client.patch(f"/api/todos/{todo['id']}", json={"title": "Read notes"}).json()
    assert updated["title"] == "Read notes"
    assert updated["due_date"] == "2026-12-01"

    cleared = client.patch(f"/api/todos/{todo['id']}", json={"due_date": None}).json()
    assert cleared["due_date"] is None
    assert cleared["title"] == "Read notes"

    assert client.patch(f"/api/todos/{todo['id']}", json={"title": None}).status_code == 422
    assert client.patch(f"/api/todos/{todo['id']}", json={"is_done": None}).status_code == 422
    assert client.patch("/api/todos/999", json={"title": "x"}).status_code == 404


def test_delete(client):
    todo = client.post("/api/todos", json={"title": "Temporary"}).json()
    assert client.delete(f"/api/todos/{todo['id']}").status_code == 204
    assert client.get(f"/api/todos/{todo['id']}").status_code == 404
    assert client.delete(f"/api/todos/{todo['id']}").status_code == 404


def test_link_to_video_and_unlink_when_video_deleted(client, db):
    video_id = add_video(db)
    todo = client.post("/api/todos", json={"title": "Take the quiz", "video_id": video_id}).json()
    assert todo["video_id"] == video_id
    assert todo["video_title"] == "Neural nets"

    assert client.delete(f"/api/videos/{video_id}").status_code == 204
    kept = client.get(f"/api/todos/{todo['id']}").json()
    assert kept["video_id"] is None
    assert kept["video_title"] is None


def test_change_and_remove_video_link(client, db):
    first, second = add_video(db, "aircAruvnKk"), add_video(db, "rfscVS0vtbw")
    todo = client.post("/api/todos", json={"title": "Study", "video_id": first}).json()

    moved = client.patch(f"/api/todos/{todo['id']}", json={"video_id": second}).json()
    assert moved["video_id"] == second
    unlinked = client.patch(f"/api/todos/{todo['id']}", json={"video_id": None}).json()
    assert unlinked["video_id"] is None and unlinked["video_title"] is None
