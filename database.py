from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///assessment.db"

engine = create_engine(
    DATABASE_URL,
    echo=False
)

Session = sessionmaker(bind=engine)

session = Session()

Base = declarative_base()

class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    role = Column(String)

class Course(Base):

    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    title = Column(String, unique=True)
    teacher_email = Column(String)

class Assessment(Base):

    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True)

    course_title = Column(String)
    title = Column(String)
    teacher_email = Column(String)

    content = Column(Text)

    difficulty = Column(String)
    question_type = Column(String)
    marks = Column(String)
    duration = Column(String)
    published = Column(String)

class Submission(Base):

    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)

    student_email = Column(String)
    course_title = Column(String)
    assessment_title = Column(String)

    answers = Column(Text)
    score = Column(String)
    feedback = Column(Text)

class RubricAssessment(Base):

    __tablename__ = "rubric_assessments"

    id = Column(Integer, primary_key=True)

    teacher_email = Column(String)
    course_title = Column(String)

    student_name = Column(String)
    file_name = Column(String)

    rubric = Column(Text)

    total_score = Column(String)
    feedback = Column(Text)

Base.metadata.create_all(engine)

