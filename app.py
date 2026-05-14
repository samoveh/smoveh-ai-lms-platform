import streamlit as st
import requests
import json
import os
import tempfile
import zipfile
import pandas as pd
import plotly.express as px

from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document as DocxReader

from database import session
from database import User
from database import Course
from database import Assessment
from database import Submission
from database import RubricAssessment

from auth import sign_up
from auth import sign_in
from auth import sign_out

from rag import process_pdf
from rag import search_knowledge

# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")

# =========================================================
# MISTRAL HELPER
# =========================================================

def ask_mistral(prompt):

    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    data = response.json()

    return data["choices"][0]["message"]["content"]

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

mode = st.sidebar.selectbox(
    "Choose Option",
    ["Login", "Signup"]
)

email = st.sidebar.text_input("Email")

password = st.sidebar.text_input(
    "Password",
    type="password"
)

role = st.sidebar.selectbox(
    "Role",
    ["Teacher", "Student"]
)

if mode == "Signup":

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

            st.success("Account created successfully")

        except Exception as e:
            st.error(str(e))

if mode == "Login":

    if st.sidebar.button("Login"):

        try:

            response = sign_in(email, password)

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

if st.session_state.logged_in:

    st.sidebar.success(
        f"Logged in as {st.session_state.user_email}"
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

    tabs = st.tabs([
        "Courses",
        "Assessments",
        "Analytics",
        "Rubric Grading"
    ])

    # =====================================================
    # COURSE TAB
    # =====================================================

    with tabs[0]:

        st.subheader("Create Course")

        course_title = st.text_input(
            "Course Title"
        )

        if st.button("Create Course"):

            existing = session.query(Course).filter_by(
                title=course_title
            ).first()

            if existing:
                st.warning("Course already exists")

            else:

                new_course = Course(
                    title=course_title,
                    teacher_email=st.session_state.user_email
                )

                session.add(new_course)
                session.commit()

                st.success("Course created")

        teacher_courses = session.query(
            Course
        ).filter_by(
            teacher_email=st.session_state.user_email
        ).all()

        if teacher_courses:

            st.subheader("Your Courses")

            for course in teacher_courses:
                st.write(course.title)

    # =====================================================
    # ASSESSMENT TAB
    # =====================================================

    with tabs[1]:

        teacher_courses = session.query(
            Course
        ).filter_by(
            teacher_email=st.session_state.user_email
        ).all()

        if teacher_courses:

            course_names = [
                c.title for c in teacher_courses
            ]

            selected_course = st.selectbox(
                "Select Course",
                course_names
            )

            assessment_title = st.text_input(
                "Assessment Title"
            )

            difficulty = st.selectbox(
                "Difficulty",
                ["Easy", "Medium", "Hard"]
            )

            question_type = st.selectbox(
                "Question Type",
                ["MCQ", "Essay", "Short Answer"]
            )

            num_questions = st.slider(
                "Number of Questions",
                1,
                20,
                5
            )

            uploaded_files = st.file_uploader(
                "Upload PDFs",
                type=["pdf"],
                accept_multiple_files=True
            )

            if uploaded_files:

                combined_text = ""

                for uploaded_file in uploaded_files:

                    temp_path = f"temp_{uploaded_file.name}"

                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.read())

                    process_pdf(temp_path)

                    reader = PdfReader(temp_path)

                    for page in reader.pages:

                        text = page.extract_text()

                        if text:
                            combined_text += text

                st.success("PDFs uploaded")

                if st.button("Generate Assessment"):

                    if question_type == "MCQ":

                        instruction = """
                        Return ONLY valid JSON.

                        [
                          {
                            "question": "",
                            "type": "MCQ",
                            "options": ["", "", "", ""],
                            "correct_answer": ""
                          }
                        ]
                        """

                    else:

                        instruction = """
                        Return ONLY valid JSON.

                        [
                          {
                            "question": "",
                            "type": "Essay",
                            "model_answer": ""
                          }
                        ]
                        """

                    prompt = f"""
                    Generate assessment questions.

                    {instruction}

                    COURSE:
                    {selected_course}

                    CONTENT:
                    {combined_text[:7000]}
                    """

                    try:

                        result = ask_mistral(prompt)

                        result = result.replace("```json", "")
                        result = result.replace("```", "")
                        result = result.strip()

                        questions = json.loads(result)

                        for index, q in enumerate(questions):

                            st.markdown(
                                f"### Question {index + 1}"
                            )

                            st.write(q["question"])

                            if q["type"] == "MCQ":

                                for option in q["options"]:
                                    st.write(f"- {option}")

                        assessment = Assessment(
                            course_title=selected_course,
                            title=assessment_title,
                            teacher_email=st.session_state.user_email,
                            content=json.dumps(questions),
                            difficulty=difficulty,
                            question_type=question_type,
                            marks="5",
                            duration="30",
                            published="Yes"
                        )

                        session.add(assessment)
                        session.commit()

                        st.success("Assessment published")

                    except Exception as e:
                        st.error(str(e))

    # =====================================================
    # ANALYTICS TAB
    # =====================================================

    with tabs[2]:

        submissions = session.query(Submission).all()

        if submissions:

            scores = []
            students = []

            for submission in submissions:

                try:
                    scores.append(int(submission.score))
                    students.append(submission.student_email)
                except:
                    pass

            if scores:

                st.metric(
                    "Average Score",
                    round(sum(scores) / len(scores), 2)
                )

                df = pd.DataFrame({
                    "Student": students,
                    "Score": scores
                })

                fig = px.bar(
                    df,
                    x="Student",
                    y="Score",
                    title="Student Performance"
                )

                st.plotly_chart(fig)

    # =====================================================
    # RUBRIC TAB
    # =====================================================

    with tabs[3]:

    st.subheader("AI Rubric Assessment")

    rubric = st.text_area(
        "Enter Your Rubric",
        height=250
    )

    uploaded_files = st.file_uploader(
        "Upload Student Files",
        type=["pdf", "docx"],
        accept_multiple_files=True
    )

    if uploaded_files and rubric:

        if st.button("Grade Submissions"):

            grading_results = []

            progress = st.progress(0)

            for index, uploaded_file in enumerate(uploaded_files):

                extracted_text = ""

                # ==========================================
                # READ PDF
                # ==========================================

                if uploaded_file.name.endswith(".pdf"):

                    reader = PdfReader(uploaded_file)

                    for page in reader.pages:

                        text = page.extract_text()

                        if text:
                            extracted_text += text

                # ==========================================
                # READ DOCX
                # ==========================================

                elif uploaded_file.name.endswith(".docx"):

                    doc = DocxReader(uploaded_file)

                    for para in doc.paragraphs:
                        extracted_text += para.text + "\n"

                # ==========================================
                # AI RUBRIC GRADING
                # ==========================================

                grading_prompt = f"""
                You are an academic evaluator.

                Grade this student work STRICTLY based on the rubric.

                RUBRIC:
                {rubric}

                STUDENT WORK:
                {extracted_text[:12000]}

                Return ONLY valid JSON:

                {{
                    "student": "{uploaded_file.name}",
                    "score": 0,
                    "grade": "",
                    "feedback": ""
                }}
                """

                try:

                    result = ask_mistral(grading_prompt)

                    result = result.replace("```json", "")
                    result = result.replace("```", "")
                    result = result.strip()

                    grading = json.loads(result)

                    grading_results.append({
                        "Student File": uploaded_file.name,
                        "Score": grading["score"],
                        "Grade": grading["grade"],
                        "Feedback": grading["feedback"]
                    })

                    rubric_record = RubricAssessment(
                        teacher_email=st.session_state.user_email,
                        course_title="General",
                        student_name=uploaded_file.name,
                        file_name=uploaded_file.name,
                        rubric=rubric,
                        total_score=str(grading["score"]),
                        feedback=grading["feedback"]
                    )

                    session.add(rubric_record)
                    session.commit()

                except Exception as e:

                    grading_results.append({
                        "Student File": uploaded_file.name,
                        "Score": "Error",
                        "Grade": "Error",
                        "Feedback": str(e)
                    })

                progress.progress(
                    (index + 1) / len(uploaded_files)
                )

            # ==========================================
            # SHOW RESULTS
            # ==========================================

            st.success("Rubric grading completed")

            df = pd.DataFrame(grading_results)

            st.dataframe(df)

            # ==========================================
            # DOWNLOAD EXCEL
            # ==========================================

            excel_file = "rubric_results.xlsx"

            df.to_excel(
                excel_file,
                index=False
            )

            with open(excel_file, "rb") as file:

                st.download_button(
                    label="Download Excel Results",
                    data=file,
                    file_name="rubric_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# =========================================================
# STUDENT DASHBOARD
# =========================================================

if (
    st.session_state.logged_in
    and st.session_state.role == "Student"
):

    st.header("Student Dashboard")

    student_tabs = st.tabs([
        "Take Exams",
        "Performance",
        "AI Tutor"
    ])

    # =====================================================
    # TAKE EXAMS
    # =====================================================

    with student_tabs[0]:

        courses = session.query(Course).all()

        if courses:

            course_names = [
                c.title for c in courses
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

                assessment_names = [
                    a.title for a in assessments
                ]

                selected_assessment_name = st.selectbox(
                    "Select Assessment",
                    assessment_names
                )

                selected_assessment = session.query(
                    Assessment
                ).filter_by(
                    title=selected_assessment_name
                ).first()

                questions = json.loads(
                    selected_assessment.content
                )

                answers = {}

                for index, q in enumerate(questions):

                    st.markdown(
                        f"### Question {index + 1}"
                    )

                    st.write(q["question"])

                    if q["type"] == "MCQ":

                        answer = st.radio(
                            "Select Answer",
                            q["options"],
                            key=f"mcq_{index}"
                        )

                    else:

                        answer = st.text_area(
                            "Your Answer",
                            key=f"essay_{index}"
                        )

                    answers[index] = answer

                if st.button("Submit Assessment"):

                    total_score = 0
                    feedbacks = []

                    for index, q in enumerate(questions):

                        grading_prompt = f"""
                        Grade this answer.

                        QUESTION:
                        {q['question']}

                        ANSWER:
                        {answers[index]}

                        Return ONLY JSON.

                        {{
                          "score": 0,
                          "feedback": ""
                        }}
                        """

                        try:

                            result = ask_mistral(
                                grading_prompt
                            )

                            result = result.replace("```json", "")
                            result = result.replace("```", "")
                            result = result.strip()

                            grading = json.loads(result)

                            total_score += int(
                                grading["score"]
                            )

                            feedbacks.append(
                                grading["feedback"]
                            )

                        except:

                            feedbacks.append(
                                "Could not grade answer"
                            )

                    submission = Submission(
                        student_email=st.session_state.user_email,
                        course_title=selected_course,
                        assessment_title=selected_assessment_name,
                        answers=json.dumps(answers),
                        score=str(total_score),
                        feedback="\\n".join(feedbacks)
                    )

                    session.add(submission)
                    session.commit()

                    st.success(
                        f"Assessment Submitted. Score: {total_score}"
                    )

                    st.subheader("AI Feedback")

                    for feedback in feedbacks:
                        st.write(feedback)

    # =====================================================
    # PERFORMANCE
    # =====================================================

    with student_tabs[1]:

        submissions = session.query(
            Submission
        ).filter_by(
            student_email=st.session_state.user_email
        ).all()

        if submissions:

            for submission in submissions:

                st.markdown(
                    f"### {submission.assessment_title}"
                )

                st.write(
                    f"Score: {submission.score}"
                )

                st.write(submission.feedback)

    # =====================================================
    # AI TUTOR
    # =====================================================

    with student_tabs[2]:

        st.subheader("AI Learning Assistant")

        question = st.text_input(
            "Ask the AI Tutor"
        )

        if st.button("Ask Tutor"):

            try:

                knowledge = search_knowledge(question)

                tutor_prompt = f"""
                Use the course material to answer.

                COURSE MATERIAL:
                {knowledge}

                QUESTION:
                {question}
                """

                response = ask_mistral(
                    tutor_prompt
                )

                st.write(response)

            except Exception as e:
                st.error(str(e))

# =========================================================
# NOT LOGGED IN
# =========================================================

if not st.session_state.logged_in:

    st.info(
        "Login or create an account to continue"
    )
