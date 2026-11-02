
import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

st.set_page_config(
    page_title="Student Management System",
    page_icon="🎓",
    layout="wide"
)

# Database
db = sqlite3.connect("students.db", check_same_thread=False)

db.execute("""
CREATE TABLE IF NOT EXISTS students (
    roll TEXT PRIMARY KEY,
    name TEXT,
    course TEXT
)
""")
db.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    roll TEXT,
    date TEXT,
    status TEXT
)
""")
db.execute("""
CREATE TABLE IF NOT EXISTS marks (
    roll TEXT,
    subject TEXT,
    marks REAL
)
""")
db.commit()


def read_data(query, params=()):
    return pd.read_sql_query(query, db, params=params).fillna("")


# PDF styles
def pdf_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=26,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=10
    ))

    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        spaceAfter=10
    ))

    styles.add(ParagraphStyle(
        name="ReportHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=colors.HexColor("#174A7E"),
        spaceBefore=8,
        spaceAfter=10
    ))

    styles.add(ParagraphStyle(
        name="ReportCell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        wordWrap="CJK"
    ))

    styles.add(ParagraphStyle(
        name="ReportHeaderCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        wordWrap="CJK"
    ))

    return styles


def pdf_footer(canvas, document):
    canvas.saveState()
    page_width = landscape(A4)[0]

    canvas.setStrokeColor(colors.HexColor("#CFD8E3"))
    canvas.line(
        15 * mm, 12 * mm,
        page_width - 15 * mm, 12 * mm
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(
        15 * mm, 7 * mm, "Student Management System"
    )
    canvas.drawRightString(
        page_width - 15 * mm, 7 * mm,
        f"Page {document.page}"
    )
    canvas.restoreState()


def make_pdf_table(data, styles):
    if data is None or data.empty:
        return Paragraph(
            "No records available.",
            styles["Normal"]
        )

    header = [
        Paragraph(escape(str(col)), styles["ReportHeaderCell"])
        for col in data.columns
    ]

    rows = [header]

    for row in data.itertuples(index=False, name=None):
        rows.append([
            Paragraph(escape(str(value)), styles["ReportCell"])
            for value in row
        ])

    page_width = landscape(A4)[0]
    usable_width = page_width - 30 * mm
    count = max(len(data.columns), 1)
    col_width = usable_width / count

    table = Table(
        rows,
        colWidths=[col_width] * count,
        repeatRows=1,
        hAlign="LEFT"
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#17365D")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#EDF3F8")]),
        ("GRID", (0, 0), (-1, -1), 0.4,
         colors.HexColor("#CFD8E3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6)
    ]))

    return table


# PDF for an individual report
def create_pdf(title, data):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = pdf_styles()

    content = [
        Paragraph("STUDENT MANAGEMENT SYSTEM", styles["ReportTitle"]),
        Paragraph(escape(str(title)), styles["ReportHeading"]),
        Paragraph(
            "Generated on " + date.today().strftime("%d %B %Y"),
            styles["ReportSubtitle"]
        ),
        Spacer(1, 10),
        make_pdf_table(data, styles)
    ]

    doc.build(
        content,
        onFirstPage=pdf_footer,
        onLaterPages=pdf_footer
    )

    return buffer.getvalue()


# PDF combining all reports
def create_complete_pdf(parts):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = pdf_styles()

    content = [
        Paragraph("STUDENT MANAGEMENT SYSTEM", styles["ReportTitle"]),
        Paragraph("Complete Report", styles["ReportHeading"]),
        Paragraph(
            "Generated on " + date.today().strftime("%d %B %Y"),
            styles["ReportSubtitle"]
        ),
        Spacer(1, 10)
    ]

    for index, (title, data) in enumerate(parts):
        if index > 0:
            content.append(PageBreak())

        content.append(
            Paragraph(escape(str(title)), styles["ReportHeading"])
        )
        content.append(make_pdf_table(data, styles))

    doc.build(
        content,
        onFirstPage=pdf_footer,
        onLaterPages=pdf_footer
    )

    return buffer.getvalue()


# Login
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🎓 Student Management System")
    st.subheader("Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Invalid username or password")

    st.stop()


# Navigation
st.sidebar.title("🎓 Student Portal")

page = st.sidebar.selectbox(
    "Choose Section",
    ["Home", "Students", "Attendance", "Marks", "PDF Report"]
)

if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

st.title("🎓 Student Management System")


# Home
if page == "Home":
    a, b, c = st.columns(3)

    a.metric(
        "Total Students",
        db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    )
    b.metric(
        "Attendance Records",
        db.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    )
    c.metric(
        "Marks Records",
        db.execute("SELECT COUNT(*) FROM marks").fetchone()[0]
    )

    st.info(
        "Manage students, attendance, marks and PDF reports "
        "from the sidebar."
    )


# Students
elif page == "Students":
    st.subheader("Add Student")

    with st.form("add_student"):
        roll = st.text_input("Roll Number")
        name = st.text_input("Student Name")
        course = st.text_input("Course")
        add = st.form_submit_button("Add Student")

    if add:
        if roll.strip() and name.strip() and course.strip():
            try:
                db.execute(
                    "INSERT INTO students (roll, name, course) "
                    "VALUES (?, ?, ?)",
                    (roll.strip(), name.strip(), course.strip())
                )
                db.commit()
                st.success("Student added successfully!")
                st.rerun()

            except sqlite3.IntegrityError:
                st.error("Roll number already exists.")

            except sqlite3.OperationalError as e:
                st.error(f"Database column issue: {e}")

        else:
            st.warning("Please fill in all fields.")

    students = read_data("SELECT * FROM students")

    st.subheader("Student List")
    st.dataframe(students, use_container_width=True)

    if not students.empty and "roll" in students.columns:
        st.subheader("Edit Roll Number")

        rolls = students["roll"].astype(str).tolist()

        old_roll = st.selectbox(
            "Select Roll Number", rolls, key="edit_roll"
        )
        new_roll = st.text_input(
            "New Roll Number", value=old_roll, key="new_roll"
        )

        if st.button("Update Roll Number"):
            new_roll = new_roll.strip()

            if not new_roll:
                st.warning("Roll number cannot be empty.")

            elif new_roll == old_roll:
                st.info("Roll number is unchanged.")

            else:
                try:
                    db.execute("BEGIN")
                    db.execute(
                        "UPDATE students SET roll=? WHERE roll=?",
                        (new_roll, old_roll)
                    )
                    db.execute(
                        "UPDATE attendance SET roll=? WHERE roll=?",
                        (new_roll, old_roll)
                    )
                    db.execute(
                        "UPDATE marks SET roll=? WHERE roll=?",
                        (new_roll, old_roll)
                    )
                    db.commit()
                    st.success("Roll number updated!")
                    st.rerun()

                except sqlite3.IntegrityError:
                    db.rollback()
                    st.error("That roll number already exists.")

                except sqlite3.OperationalError as e:
                    db.rollback()
                    st.error(f"Could not update roll number: {e}")

        st.subheader("Delete Student")

        delete_roll = st.selectbox(
            "Select Roll Number to Delete",
            rolls,
            key="delete_roll"
        )
        confirm = st.checkbox("Confirm student deletion")

        if st.button("Delete Student"):
            if confirm:
                db.execute(
                    "DELETE FROM attendance WHERE roll=?",
                    (delete_roll,)
                )
                db.execute(
                    "DELETE FROM marks WHERE roll=?",
                    (delete_roll,)
                )
                db.execute(
                    "DELETE FROM students WHERE roll=?",
                    (delete_roll,)
                )
                db.commit()
                st.success("Student and related records deleted.")
                st.rerun()
            else:
                st.warning("Please confirm deletion.")


# Attendance
elif page == "Attendance":
    st.subheader("Record Attendance")
    students = read_data("SELECT roll, name FROM students")

    if students.empty:
        st.warning("Add a student first.")

    else:
        options = {
            f"{row['roll']} - {row['name']}": row["roll"]
            for _, row in students.iterrows()
        }

        choice = st.selectbox("Student", list(options.keys()))
        attend_date = st.date_input("Date", value=date.today())
        status = st.selectbox("Status", ["Present", "Absent"])

        if st.button("Save Attendance"):
            db.execute(
                "INSERT INTO attendance (roll, date, status) "
                "VALUES (?, ?, ?)",
                (options[choice], str(attend_date), status)
            )
            db.commit()
            st.success("Attendance saved!")

    st.dataframe(
        read_data("SELECT * FROM attendance"),
        use_container_width=True
    )


# Marks
elif page == "Marks":
    st.subheader("Enter Marks")
    students = read_data("SELECT roll, name FROM students")

    if students.empty:
        st.warning("Add a student first.")

    else:
        options = {
            f"{row['roll']} - {row['name']}": row["roll"]
            for _, row in students.iterrows()
        }

        choice = st.selectbox("Student", list(options.keys()))
        subject = st.text_input("Subject")
        marks = st.number_input(
            "Marks", min_value=0.0, max_value=100.0
        )

        if st.button("Save Marks"):
            if subject.strip():
                db.execute(
                    "INSERT INTO marks (roll, subject, marks) "
                    "VALUES (?, ?, ?)",
                    (options[choice], subject.strip(), marks)
                )
                db.commit()
                st.success("Marks saved!")
            else:
                st.warning("Enter a subject.")

    st.dataframe(
        read_data("SELECT * FROM marks"),
        use_container_width=True
    )


# PDF Reports
elif page == "PDF Report":
    st.subheader("📄 PDF Reports")

    kind = st.selectbox(
        "Select Report",
        ["Students", "Attendance", "Marks", "Complete Report"]
    )

    queries = {
        "Students": "SELECT * FROM students",
        "Attendance": "SELECT * FROM attendance",
        "Marks": "SELECT * FROM marks"
    }

    if kind != "Complete Report":
        data = read_data(queries[kind])
        st.dataframe(data, use_container_width=True)

    if st.button("Generate PDF"):
        if kind == "Complete Report":
            parts = [
                ("Students Report", read_data(queries["Students"])),
                ("Attendance Report", read_data(queries["Attendance"])),
                ("Marks Report", read_data(queries["Marks"]))
            ]

            pdf_bytes = create_complete_pdf(parts)

        else:
            pdf_bytes = create_pdf(
                kind + " Report",
                read_data(queries[kind])
            )

        st.download_button(
            "⬇️ Download PDF",
            data=pdf_bytes,
            file_name=kind.lower().replace(" ", "_") + "_report.pdf",
            mime="application/pdf"
        )
