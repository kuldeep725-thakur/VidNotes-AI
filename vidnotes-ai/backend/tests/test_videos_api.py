from app.models import LOCAL_USER_ID, Video, VideoStatus


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["groq_configured"] is True


def test_invalid_url_is_rejected(client):
    response = client.post("/api/videos", json={"url": "https://vimeo.com/123456"})
    assert response.status_code == 422
    assert "valid YouTube" in response.json()["detail"]


def test_analyze_creates_one_record_per_video(client):
    first = client.post("/api/videos", json={"url": "https://youtu.be/aircAruvnKk", "quiz_count": 5})
    assert first.status_code == 202
    assert first.json()["status"] == "processing"

    again = client.post("/api/videos", json={"url": "https://www.youtube.com/watch?v=aircAruvnKk&t=9s"})
    assert again.json()["id"] == first.json()["id"]
    assert len(client.get("/api/videos").json()) == 1


def test_quiz_count_limits(client):
    for count in (4, 21):
        response = client.post("/api/videos", json={"url": "https://youtu.be/aircAruvnKk", "quiz_count": count})
        assert response.status_code == 422


def test_processing_video_cannot_be_deleted_or_exported(client):
    video_id = client.post("/api/videos", json={"url": "https://youtu.be/aircAruvnKk"}).json()["id"]
    assert client.delete(f"/api/videos/{video_id}").status_code == 409
    assert client.get(f"/api/videos/{video_id}/pdf?language=en").status_code == 409


def test_search_and_not_found(client, db):
    db.add_all([
        Video(user_id=LOCAL_USER_ID, youtube_id="aircAruvnKk", url="u1", title="Neural networks",
              status=VideoStatus.COMPLETED),
        Video(user_id=LOCAL_USER_ID, youtube_id="rfscVS0vtbw", url="u2", title="Learn Python",
              status=VideoStatus.COMPLETED),
    ])
    db.commit()
    assert [v["title"] for v in client.get("/api/videos?search=python").json()] == ["Learn Python"]
    assert client.get("/api/videos?search=%25").json() == []
    assert client.get("/api/videos/999").status_code == 404


def test_request_size_limit(client):
    response = client.post("/api/videos", content="x" * 20_000, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
