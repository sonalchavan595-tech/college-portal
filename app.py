
import streamlit as st
import sqlite3
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas

st.set_page_config(
    page_title="College Management Portal",
    page_icon="🎓",
    layout="wide"
)

# Professional Blue Theme
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #eaf2ff, #ffffff);
}
[data-testid="stSidebar"] {
    background-color: #16345c;
}
[data-testid="stSidebar"] * {
    color: white;
}
h1, h2, h3 {
    color: #16345c;
}
.stButton > button {
    background-color: #1e40af;
    color: white;
    border-radius: 8px;
    border: none;
}
.stButton > button:hover {
    background-color: #16345c;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# Database connection
db = sqlite3.connect("students.db", check_same_thread=False)

db.execute("""
CREATE TABLE IF NOT EXISTS students (
    name TEXT,
    roll TEXT UNIQUE,
    course TEXT
)
""")
db.execute("""
CREATE TABLE IF NOT EXISTS marks (
    roll TEXT,
    subject TEXT,
    marks REAL
)
""")
db.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    roll TEXT,
    day TEXT,
    status TEXT
)
""")
db.commit()

st.title("🎓 College Management Portal")
st.caption("Student Records | Attendance | Marks | Reports")

# Login
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.subheader("Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Incorrect username or password.")
    st.stop()

# Navigation
page = st.sidebar.radio(
    "Navigation",
    ["Home", "Students", "Attendance", "Marks", "PDF Report"]
)

if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

# Read student records
try:
    students = db.execute(
        "SELECT name, roll, course FROM students"
    ).fetchall()
except sqlite3.OperationalError as e:
    st.error("Database columns need checking: " + str(e))
    st.stop()

# Dashboard
if page == "Home":
    st.header("📊 Dashboard")

    attendance_count = db.execute(
        "SELECT COUNT(*) FROM attendance"
    ).fetchone()[0]
    marks_count = db.execute(
        "SELECT COUNT(*) FROM marks"
    ).fetchone()[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Students", len(students))
    col2.metric("Attendance Records", attendance_count)
    col3.metric("Marks Records", marks_count)

    st.success("Welcome to your College Portal!")

# Student Management
elif page == "Students":
    st.header("👨‍🎓 Student Management")

    action = st.radio(
        "Select Action",
        ["Add", "Edit", "Delete"],
        horizontal=True
    )

    if action == "Add":
        with st.form("add_student"):
            name = st.text_input("Student Name")
            roll = st.text_input("Roll Number")
            course = st.selectbox(
                "Course",
                ["BCA", "BBA", "BSc", "BCom", "BA", "BTech", "MCA"]
            )
            submitted = st.form_submit_button("Add Student")

        if submitted:
            if name.strip() and roll.strip():
                try:
                    db.execute(
                        "INSERT INTO students (name, roll, course) VALUES (?, ?, ?)",
                        (name.strip(), roll.strip(), course)
                    )
                    db.commit()
                    st.success("Student added successfully!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Roll number already exists.")
                except sqlite3.OperationalError as e:
                    st.error("Database column mismatch: " + str(e))
            else:
                st.warning("Enter name and roll number.")

    elif action == "Edit":
        if students:
            student = st.selectbox(
                "Select Student",
                students,
                format_func=lambda s: f"{s[0]} - {s[1]}"
            )
            new_name = st.text_input("Name", student[0])
            new_course = st.text_input("Course", student[2] or "")

            if st.button("Update Student"):
                db.execute(
                    "UPDATE students SET name=?, course=? WHERE roll=?",
                    (new_name.strip(), new_course.strip(), student[1])
                )
                db.commit()
                st.success("Student updated!")
                st.rerun()
        else:
            st.info("No students available.")

    elif action == "Delete":
        if students:
            student = st.selectbox(
                "Select Student to Delete",
                students,
                format_func=lambda s: f"{s[0]} - {s[1]}"
            )
            if st.button("Delete Student"):
                db.execute(
                    "DELETE FROM students WHERE roll=?",
                    (student[1],)
                )
                db.commit()
                st.success("Student deleted.")
                st.rerun()
        else:
            st.info("No students available.")

    st.subheader("Student List")
    st.dataframe(
        pd.DataFrame(students, columns=["Name", "Roll", "Course"]),
        use_container_width=True
    )

# Attendance
elif page == "Attendance":
    st.header("📅 Attendance Management")

    if students:
        student = st.selectbox(
            "Select Student",
            students,
            format_func=lambda s: f"{s[0]} - {s[1]}"
        )
        day = st.date_input("Date")
        status = st.selectbox("Status", ["Present", "Absent"])

        if st.button("Save Attendance"):
            db.execute(
                "DELETE FROM attendance WHERE roll=? AND day=?",
                (student[1], str(day))
            )
            db.execute(
                "INSERT INTO attendance (roll, day, status) VALUES (?, ?, ?)",
                (student[1], str(day), status)
            )
            db.commit()
            st.success("Attendance saved!")
            st.rerun()

        records = db.execute(
            "SELECT day, status FROM attendance WHERE roll=? ORDER BY day DESC",
            (student[1],)
        ).fetchall()

        st.dataframe(
            pd.DataFrame(records, columns=["Date", "Status"]),
            use_container_width=True
        )

        if records:
            percentage = (
                sum(row[1] == "Present" for row in records)
                / len(records) * 100
            )
            st.metric("Attendance Percentage", f"{percentage:.1f}%")
    else:
        st.info("Add a student first.")

# Marks
elif page == "Marks":
    st.header("📝 Marks Management")

    if students:
        student = st.selectbox(
            "Select Student",
            students,
            format_func=lambda s: f"{s[0]} - {s[1]}"
        )
        subject = st.text_input("Subject")
        mark = st.number_input(
            "Marks out of 100",
            min_value=0.0,
            max_value=100.0,
            step=1.0
        )

        if st.button("Save Marks"):
            if subject.strip():
                db.execute(
                    "DELETE FROM marks WHERE roll=? AND subject=?",
                    (student[1], subject.strip())
                )
                db.execute(
                    "INSERT INTO marks (roll, subject, marks) VALUES (?, ?, ?)",
                    (student[1], subject.strip(), mark)
                )
                db.commit()
                st.success("Marks saved!")
                st.rerun()
            else:
                st.warning("Enter a subject name.")

        records = db.execute(
            "SELECT subject, marks FROM marks WHERE roll=?",
            (student[1],)
        ).fetchall()

        st.dataframe(
            pd.DataFrame(records, columns=["Subject", "Marks"]),
            use_container_width=True
        )

        if records:
            average = sum(row[1] for row in records) / len(records)
            grade = (
                "A" if average >= 80
                else "B" if average >= 60
                else "C" if average >= 40
                else "Needs Improvement"
            )

            col1, col2 = st.columns(2)
            col1.metric("Average Percentage", f"{average:.1f}%")
            col2.metric("Grade", grade)
    else:
        st.info("Add a student first.")

# PDF Report
elif page == "PDF Report":
    st.header("📄 Student PDF Report")

    if students:
        student = st.selectbox(
            "Select Student",
            students,
            format_func=lambda s: f"{s[0]} - {s[1]}"
        )

        records = db.execute(
            "SELECT subject, marks FROM marks WHERE roll=?",
            (student[1],)
        ).fetchall()

        if st.button("Generate PDF"):
            buffer = BytesIO()
            pdf = canvas.Canvas(buffer)

            pdf.setFont("Helvetica-Bold", 18)
            pdf.drawString(50, 800, "COLLEGE MARKSHEET")
            pdf.setFont("Helvetica", 12)
            pdf.drawString(50, 765, f"Name: {student[0]}")
            pdf.drawString(50, 745, f"Roll Number: {student[1]}")
            pdf.drawString(50, 725, f"Course: {student[2]}")

            y = 685
            for subject_name, marks_value in records:
                if y < 60:
                    pdf.showPage()
                    y = 800
                pdf.drawString(
                    50, y, f"{subject_name}: {marks_value}/100"
                )
                y -= 25

            if records:
                average = sum(row[1] for row in records) / len(records)
                pdf.drawString(50, y - 15, f"Average: {average:.1f}%")

            pdf.save()

            st.download_button(
                "Download PDF",
                data=buffer.getvalue(),
                file_name="marksheet.pdf",
                mime="application/pdf"
            )
    else:
        st.info("Add a student first.")

db.close()
