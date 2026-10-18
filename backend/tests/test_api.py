def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_create_course(client):
    resp = client.post("/api/courses/", json={"name": "Test Course", "platform": "udemy"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Course"
    assert data["platform"] == "udemy"
    assert "id" in data


def test_list_courses(client):
    resp = client.get("/api/courses/")
    assert resp.status_code == 200
    count_before = len(resp.json())
    client.post("/api/courses/", json={"name": "Course A"})
    client.post("/api/courses/", json={"name": "Course B"})
    resp = client.get("/api/courses/")
    assert resp.status_code == 200
    assert len(resp.json()) == count_before + 2


def test_get_course(client):
    create = client.post("/api/courses/", json={"name": "My Course"}).json()
    resp = client.get(f"/api/courses/{create['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "My Course"


def test_get_course_not_found(client):
    resp = client.get("/api/courses/999")
    assert resp.status_code == 404


def test_delete_course(client):
    create = client.post("/api/courses/", json={"name": "Delete Me"}).json()
    resp = client.delete(f"/api/courses/{create['id']}")
    assert resp.status_code == 200
    resp = client.get(f"/api/courses/{create['id']}")
    assert resp.status_code == 404


def test_create_lesson(client, db_session):
    from app.models.course import Course, Module
    course = Course(name="Test")
    db_session.add(course)
    db_session.commit()
    mod = Module(course_id=course.id, name="Module 1")
    db_session.add(mod)
    db_session.commit()

    resp = client.post(
        "/api/lessons/",
        json={"module_id": mod.id, "title": "Lesson 1"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Lesson 1"


def test_update_lesson_progress(client, db_session):
    from app.models.course import Course, Module
    from app.models.lesson import Lesson
    course = Course(name="Test")
    db_session.add(course)
    db_session.commit()
    mod = Module(course_id=course.id, name="Mod")
    db_session.add(mod)
    db_session.commit()
    lesson = Lesson(module_id=mod.id, title="Test Lesson")
    db_session.add(lesson)
    db_session.commit()

    resp = client.post(f"/api/lessons/{lesson.id}/progress?completed=true")
    assert resp.status_code == 200
    assert resp.json()["completed"] is True


def test_create_flashcard(client):
    resp = client.post(
        "/api/flashcards/",
        json={"lesson_id": 1, "front": "Question?", "back": "Answer!"},
    )
    assert resp.status_code == 200
    assert resp.json()["front"] == "Question?"


def test_flashcard_stats(client, db_session):
    from app.models.flashcard import Flashcard
    resp = client.get("/api/flashcards/stats")
    before = resp.json()["total"]
    fc = Flashcard(lesson_id=1, front="Q", back="A")
    db_session.add(fc)
    db_session.commit()

    resp = client.get("/api/flashcards/stats")
    assert resp.status_code == 200
    assert resp.json()["total"] == before + 1


def test_dashboard(client):
    resp = client.get("/api/analytics/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "lessons_completed" in data
    assert "study_time_minutes" in data
