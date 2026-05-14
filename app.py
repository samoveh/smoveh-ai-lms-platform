import streamlit as st
from mistralai import Client
from pypdf import PdfReader
from dotenv import load_dotenv
from docx import Document
import zipfile
import tempfile
import pandas as pd
import plotly.express as px
import os
import json

from docx import Document as DocxReader

from database import User
from database import Course
from database import Assessment
from database import Submission
from database import RubricAssessment
from database import session

from auth import sign_up
from auth import sign_in
from auth import sign_out

from rag import process_pdf
from rag import search_knowledge

# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")

client = Client(api_key=api_key)

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI LMS Platform",
    layout="wide"
)

st.title("AI Assessment & Learning Platform")

# =========================================================
# SESSION STATE
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if "role" not in st.session_state:
    st.session_state.role = ""

# =========================================================
# AUTHENTICATION
# =========================================================

st.sidebar.title("Authentication")

auth_mode = st.sidebar.selectbox(
    "Choose Option",
    ["Login", "Signup"]
)

email = st.sidebar.text_input("Email")

password = st.sidebar.text_input(
    "Password",
    type="password"
)

role = st.sidebar.selectbox(
    "Select Role",
    ["Teacher", "Student"]
)

# =========================================================
# SIGNUP
# =========================================================

if auth_mode == "Signup":

    if st.sidebar.button("Create Account"):

        try:

            sign_up(email, password)

            existing_user = session.query(User).filter_by(
                email=email
            ).first()

            if not existing_user:

                new_user = User(
                    email=email,
                    role=role
                )

                session.add(new_user)

                session.commit()

            st.success(
                "Account created successfully!"
            )

        except Exception as e:

            st.error(str(e))

# =========================================================
# LOGIN
# =========================================================

if auth_mode == "Login":

    if st.sidebar.button("Login"):

        try:

            response = sign_in(
                email,
                password
            )

            if hasattr(response, "user"):

                st.session_state.logged_in = True

                st.session_state.user_email = email

                user = session.query(User).filter_by(
                    email=email
                ).first()

                if user:
                    st.session_state.role = user.role

                st.rerun()

        except Exception as e:

            st.error(str(e))

# =========================================================
# LOGOUT
# =========================================================

if st.session_state.logged_in:

    st.sidebar.success(
        f"Logged in as: {st.session_state.user_email}"
    )

    st.sidebar.success(
        f"Role: {st.session_state.role}"
    )

    if st.sidebar.button("Logout"):

        sign_out()

        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.role = ""

        st.rerun()

# =========================================================
# TEACHER DASHBOARD
# =========================================================

if (
    st.session_state.logged_in
    and st.session_state.role == "Teacher"
):

    st.header("Teacher Dashboard")

    # =====================================================
    # CREATE COURSE
    # =====================================================

    st.subheader("Create Course")

    course_title = st.text_input(
        "Course Title"
    )

    if st.button("Create Course"):

        existing_course = session.query(Course).filter_by(
            title=course_title
        ).first()

        if existing_course:

            st.warning(
                "Course already exists."
            )

        else:

            new_course = Course(
                title=course_title,
                teacher_email=st.session_state.user_email
            )

            session.add(new_course)

            session.commit()

            st.success(
                "Course created successfully!"
            )

    # =====================================================
    # COURSE SELECTION
    # =====================================================

    teacher_courses = session.query(
        Course
    ).filter_by(
        teacher_email=st.session_state.user_email
    ).all()

    if teacher_courses:

        course_options = [
            course.title
            for course in teacher_courses
        ]

        selected_course = st.selectbox(
            "Select Course",
            course_options
        )

        # =================================================
        # COURSE ANALYTICS
        # =================================================

        st.subheader("Course Analytics")

        all_submissions = session.query(
            Submission
        ).filter_by(
            course_title=selected_course
        ).all()

        if all_submissions:

            scores = []

            for submission in all_submissions:

                try:
                    scores.append(
                        int(submission.score)
                    )
                except:
                    pass

            if scores:

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Total Submissions",
                    len(scores)
                )

                col2.metric(
                    "Average Score",
                    round(
                        sum(scores) / len(scores),
                        2
                    )
                )

                col3.metric(
                    "Highest Score",
                    max(scores)
                )

        # =================================================
        # CREATE ASSESSMENT
        # =================================================

        st.subheader("Create Assessment")

        assessment_title = st.text_input(
            "Assessment Title"
        )

        num_questions = st.slider(
            "Number of Questions",
            1,
            20,
            5
        )

        difficulty = st.selectbox(
            "Difficulty",
            ["Easy", "Medium", "Hard"]
        )

        question_type = st.selectbox(
            "Question Type",
            ["Essay", "Short Answer", "MCQ"]
        )

        marks = st.selectbox(
            "Marks Per Question",
            [2, 5, 10]
        )

        uploaded_files = st.file_uploader(
            "Upload PDFs",
            type="pdf",
            accept_multiple_files=True
        )

        if uploaded_files:

            combined_text = ""

            for uploaded_file in uploaded_files:

                temp_file = f"temp_{uploaded_file.name}"

                with open(temp_file, "wb") as f:
                    f.write(uploaded_file.read())

                process_pdf(temp_file)

                reader = PdfReader(temp_file)

                for page in reader.pages:

                    extracted = page.extract_text()

                    if extracted:
                        combined_text += extracted

            st.success(
                "PDFs uploaded successfully!"
            )

            if st.button("Generate Assessment"):

                if question_type == "MCQ":

                    format_instruction = """
                    Return ONLY valid JSON.

                    [
                      {
                        "question": "",
                        "type": "MCQ",
                        "options": [
                          "",
                          "",
                          "",
                          ""
                        ],
                        "correct_answer": "",
                        "marks": 0
                      }
                    ]
                    """

                else:

                    format_instruction = """
                    Return ONLY valid JSON.

                    [
                      {
                        "question": "",
                        "type": "",
                        "model_answer": "",
                        "marks": 0
                      }
                    ]
                    """

                prompt = f"""
                Generate assessment questions.

                {format_instruction}

                Course:
                {selected_course}

                Number of Questions:
                {num_questions}

                Difficulty:
                {difficulty}

                Lecture Material:
                {combined_text[:8000]}
                """

                try:

                    response = client.chat.complete(
                        model="mistral-small-latest",
                        messages=[
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    )

                    result = response.choices[0].message.content

                    result = result.replace(
                        "```json",
                        ""
                    )

                    result = result.replace(
                        "```",
                        ""
                    )

                    result = result.strip()

                    questions = json.loads(result)

                    st.subheader(
                        "Generated Assessment"
                    )

                    for index, question_data in enumerate(questions):

                        st.markdown(
                            f"## Question {index + 1}"
                        )

                        st.write(
                            question_data["question"]
                        )

                        if question_data["type"] == "MCQ":

                            for option in question_data["options"]:

                                st.write(f"- {option}")

                    new_assessment = Assessment(
                        course_title=selected_course,
                        title=assessment_title,
                        teacher_email=st.session_state.user_email,
                        content=json.dumps(questions),
                        difficulty=difficulty,
                        question_type=question_type,
                        marks=str(marks),
                        duration="30",
                        published="Yes"
                    )

                    session.add(new_assessment)

                    session.commit()

                    st.success(
                        "Assessment Published!"
                    )

                except Exception as e:

                    st.error(str(e))

# =========================================================
# STUDENT DASHBOARD
# =========================================================

if (
    st.session_state.logged_in
    and st.session_state.role == "Student"
):

    st.header("Student Dashboard")

    available_courses = session.query(
        Course
    ).all()

    if available_courses:

        course_names = [
            course.title
            for course in available_courses
        ]

        selected_course = st.selectbox(
            "Select Course",
            course_names
        )

        assessments = session.query(
            Assessment
        ).filter_by(
            course_title=selected_course
        ).all()

        if assessments:

            assessment_titles = [
                assessment.title
                for assessment in assessments
            ]

            selected_assessment_title = st.selectbox(
                "Select Assessment",
                assessment_titles
            )

            selected_assessment = session.query(
                Assessment
            ).filter_by(
                title=selected_assessment_title
            ).first()

            questions = json.loads(
                selected_assessment.content
            )

            st.subheader("Assessment Questions")

            student_answers = {}

            for index, question in enumerate(questions):

                st.markdown(
                    f"### Question {index + 1}"
                )

                st.write(question["question"])

                if question["type"] == "MCQ":

                    answer = st.radio(
                        "Select Answer",
                        question["options"],
                        key=f"mcq_{index}"
                    )

                else:

                    answer = st.text_area(
                        "Your Answer",
                        key=f"text_{index}"
                    )

                student_answers[index] = answer

            if st.button("Submit Assessment"):

                total_score = 0

                feedback_list = []

                for index, question in enumerate(questions):

                    student_answer = student_answers[index]

                    grading_prompt = f"""
                    Grade the student answer.

                    QUESTION:
                    {question['question']}

                    STUDENT ANSWER:
                    {student_answer}

                    Return ONLY valid JSON.

                    {{
                      "score": 0,
                      "feedback": ""
                    }}
                    """

                    try:

                        response = client.chat.complete(
                            model="mistral-small-latest",
                            messages=[
                                {
                                    "role": "user",
                                    "content": grading_prompt
                                }
                            ]
                        )

                        result = response.choices[0].message.content

                        result = result.replace(
                            "```json",
                            ""
                        )

                        result = result.replace(
                            "```",
                            ""
                        )

                        result = result.strip()

                        grading_data = json.loads(result)

                        total_score += int(
                            grading_data["score"]
                        )

                        feedback_list.append(
                            grading_data["feedback"]
                        )

                    except:

                        feedback_list.append(
                            "Could not grade answer."
                        )

                submission = Submission(
                    student_email=st.session_state.user_email,
                    course_title=selected_course,
                    assessment_title=selected_assessment_title,
                    answers=json.dumps(student_answers),
                    score=str(total_score),
                    feedback="\n".join(feedback_list)
                )

                session.add(submission)

                session.commit()

                st.success(
                    f"Assessment Submitted! Score: {total_score}"
                )

                st.subheader("AI Feedback")

                for feedback in feedback_list:
                    st.write(feedback)

            # =================================================
            # AI TUTOR
            # =================================================

            st.markdown("---")

            st.subheader("AI Tutor")

            tutor_question = st.text_input(
                "Ask the AI Tutor"
            )

            if st.button("Ask Tutor"):

                knowledge = search_knowledge(
                    tutor_question
                )

                tutor_prompt = f"""
                Use the course material below to answer.

                COURSE MATERIAL:
                {knowledge}

                QUESTION:
                {tutor_question}
                """

                try:

                    response = client.chat.complete(
                        model="mistral-small-latest",
                        messages=[
                            {
                                "role": "user",
                                "content": tutor_prompt
                            }
                        ]
                    )

                    tutor_response = response.choices[
                        0
                    ].message.content

                    st.write(tutor_response)

                except Exception as e:
                    st.error(str(e))

if not st.session_state.logged_in:

    st.warning(
        "Please login or create an account."
    )