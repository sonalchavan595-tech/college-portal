import streamlit as st
import sqlite3
from io import BytesIO
from reportlab.pdfgen import canvas

st.set_page_config(page_title="College Portal", page_icon="🎓")
st.markdown("""
<style>
.stApp {background:#f0f5ff}
h1,h2 {color:#174078}
</style>
""", unsafe_allow_html=True)

db = sqlite3.connect("students.db")
db.execute("CREATE TABLE IF NOT EXISTS students(name TEXT, roll TEXT UNIQUE, course TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS marks(roll TEXT, subject TEXT, marks REAL)")
db.execute("CREATE TABLE IF NOT EXISTS attendance(roll TEXT, day TEXT, status TEXT)")
db.commit()

st.title("🎓 College Management Portal")

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "admin123":
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Wrong login")
    st.stop()

page = st.sidebar.radio("Menu", [
    "Home", "Students", "Attendance", "Marks"
])
students = db.execute("SELECT name,roll,course FROM students").fetchall()

if page == "Home":
    st.metric("Total Students", len(students))

elif page == "Students":
    action = st.radio("Action", ["Add", "Edit", "Delete"])
    if action == "Add":
        n = st.text_input("Name")
        r = st.text_input("Roll")
        c = st.text_input("Course")
        if st.button("Save"):
            try:
                db.execute("INSERT INTO students VALUES(?,?,?)",(n,r,c))
                db.commit()
                st.success("Saved!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Roll already exists")
    elif students:
        s = st.selectbox("Student", students, format_func=lambda x:f"{x[0]} - {x[1]}")
        if action == "Delete":
            if st.button("Delete student"):
                db.execute("DELETE FROM students WHERE roll=?",(s[1],))
                db.commit()
                st.rerun()
        else:
            n = st.text_input("New name", s[0])
            c = st.text_input("New course", s[2] or "")
            if st.button("Update"):
                db.execute("UPDATE students SET name=?,course=? WHERE roll=?",(n,c,s[1]))
                db.commit()
                st.success("Updated!")
                st.rerun()
    st.dataframe(students)

elif page == "Attendance":
    if students:
        s = st.selectbox("Student", students, format_func=lambda x:x[0])
        d = st.date_input("Date")
        status = st.selectbox("Status", ["Present","Absent"])
        if st.button("Save attendance"):
            db.execute("DELETE FROM attendance WHERE roll=? AND day=?",(s[1],str(d)))
            db.execute("INSERT INTO attendance VALUES(?,?,?)",(s[1],str(d),status))
            db.commit()
            st.rerun()
        rows = db.execute("SELECT day,status FROM attendance WHERE roll=?",(s[1],)).fetchall()
        st.dataframe(rows)
        if rows:
            pct = sum(x[1]=="Present" for x in rows)/len(rows)*100
            st.metric("Attendance",f"{pct:.1f}%")

elif page == "Marks":
    if students:
        s = st.selectbox("Student", students, format_func=lambda x:x[0])
        sub = st.text_input("Subject")
        m = st.number_input("Marks",0,100)
        if st.button("Save marks") and sub:
            db.execute("DELETE FROM marks WHERE roll=? AND subject=?",(s[1],sub))
            db.execute("INSERT INTO marks VALUES(?,?,?)",(s[1],sub,m))
            db.commit()
            st.rerun()
        rows = db.execute("SELECT subject,marks FROM marks WHERE roll=?",(s[1],)).fetchall()
        st.dataframe(rows)
        if rows:
            avg = sum(x[1] for x in rows)/len(rows)
            st.metric("Percentage",f"{avg:.1f}%")
            st.metric("Grade","A" if avg>=80 else "B" if avg>=60 else "C")
            pdf = BytesIO()
            c = canvas.Canvas(pdf)
            c.drawString(70,800,"COLLEGE MARKSHEET")
            c.drawString(70,770,f"Name: {s[0]}  Roll: {s[1]}")
            y = 730
            for subject, marks in rows:
                c.drawString(70,y,f"{subject}: {marks}/100")
                y -= 25
            c.drawString(70,y-20,f"Percentage: {avg:.1f}%")
            c.save()
            st.download_button("Download PDF",pdf.getvalue(),"marksheet.pdf")

db.close()