from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta, timezone
from app.models.course import Course, Module
from app.models.lesson import Lesson, LessonProgress
from app.models.note import Note, RevisionQuestion
from app.models.flashcard import Flashcard, FlashcardReview
from app.models.coding import CodingProblem, CodingSolution, CodingHint
from app.models.mcq import MCQQuestion, MCQOption
from app.models.analytics import StudySession, WeakArea, RevisionSchedule
from app.schemas.analytics import DashboardStats


class KnowledgeBase:
    def get_dashboard_stats(self, db: Session) -> DashboardStats:
        total_lessons = db.query(Lesson).count()
        completed = db.query(LessonProgress).filter(LessonProgress.completed == True).count()
        study_sessions = db.query(StudySession).all()
        total_seconds = sum(s.duration_seconds for s in study_sessions)
        concepts = db.query(Note).count()
        weak_areas = db.query(WeakArea).all()
        flashcards_due = db.query(Flashcard).count()

        next_rev = (
            db.query(RevisionSchedule)
            .filter(RevisionSchedule.next_review <= datetime.now(timezone.utc))
            .order_by(RevisionSchedule.next_review)
            .first()
        )

        return DashboardStats(
            lessons_completed=completed,
            total_lessons=max(total_lessons, 1),
            study_time_minutes=round(total_seconds / 60, 1),
            concepts_learned=concepts,
            weak_areas=[w.concept for w in weak_areas],
            flashcards_due=flashcards_due,
            next_revision=str(next_rev.next_review) if next_rev else None,
        )

    def save_course(self, db: Session, name: str, platform: Optional[str] = None, url: Optional[str] = None) -> Course:
        course = Course(name=name, platform=platform, url=url)
        db.add(course)
        db.commit()
        db.refresh(course)
        return course

    def save_lesson_progress(self, db: Session, lesson_id: int, completed: bool = True) -> LessonProgress:
        progress = db.query(LessonProgress).filter(LessonProgress.lesson_id == lesson_id).first()
        if not progress:
            progress = LessonProgress(lesson_id=lesson_id, completed=completed)
            db.add(progress)
        else:
            progress.completed = completed
            if completed:
                progress.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(progress)
        return progress

    def save_notes(self, db: Session, lesson_id: int, summary: str, detailed: str, concepts: str) -> Note:
        note = Note(
            lesson_id=lesson_id,
            summary=summary,
            detailed_notes=detailed,
            key_concepts=concepts,
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    def save_revision_question(self, db: Session, note_id: int, question: str, answer: str) -> RevisionQuestion:
        rq = RevisionQuestion(note_id=note_id, question=question, answer=answer)
        db.add(rq)
        db.commit()
        db.refresh(rq)
        return rq

    def save_flashcards(self, db: Session, lesson_id: int, cards: list[dict]) -> list[Flashcard]:
        saved = []
        for card in cards:
            fc = Flashcard(lesson_id=lesson_id, front=card["front"], back=card["back"])
            db.add(fc)
            saved.append(fc)
        db.commit()
        for fc in saved:
            db.refresh(fc)
        return saved

    def save_coding_problem(self, db: Session, lesson_id: int, title: str, description: str, template: Optional[str] = None) -> CodingProblem:
        problem = CodingProblem(lesson_id=lesson_id, title=title, description=description, solution_template=template)
        db.add(problem)
        db.commit()
        db.refresh(problem)
        return problem

    def save_study_session(self, db: Session, course_id: Optional[int], lesson_id: Optional[int], duration: int, session_type: str = "lecture") -> StudySession:
        session = StudySession(
            course_id=course_id,
            lesson_id=lesson_id,
            duration_seconds=duration,
            session_type=session_type,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session


knowledge_base = KnowledgeBase()
