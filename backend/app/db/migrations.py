from app.database import engine, Base
from app.db.base import *


def run_migrations():
    Base.metadata.create_all(bind=engine)
