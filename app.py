
import streamlit as st, sqlite3, pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas

st.set_page_config(page_title="College Portal",page_icon="🎓",layout="wide")
st.markdown("""
<style>
.stApp{background:#F4F7FB;color:#12305A}
h1,h2,h3,p,label,[data-testid="stWidgetLabel"] p{color:#12305A!important}
[data-testid="stSidebar"]{background:#12305A}
[data-testid="stSidebar"] *{color:white!important}
[data-testid="stTextInput"] input{background:white!important;color:#12305A!important}
.stButton button,.stFormSubmitButton button{background:#1D4ED8!important;color:white!important}
[data-testid="stMetric"]{background:white;padding:10px;border-radius:10px}
@media(max-width:768px){.block-container{padding:.7rem!important}h1{font-size:1.6rem!important}}
</style>""",unsafe_allow_html=True)

db=sqlite3.connect("students.db",check_same_thread=False)
db.executescript("""
CREATE TABLE IF NOT EXISTS students(name TEXT,roll TEXT UNIQUE,course TEXT);
CREATE TABLE IF NOT EXISTS attendance(roll TEXT,day TEXT,status TEXT);
CREATE TABLE IF NOT EXISTS marks(roll TEXT,subject TEXT,marks REAL);
""")
db.commit()
st.title("🎓 College Portal")

if "logged_in" not in st.session_state: st.session_state.logged_in=False
if not st.session_state.logged_in:
    with st.form("login"):
        u=st.text_input("Username"); p=st.text_input("Password",type="password")
        ok=st.form_submit_button("Login")
    if ok:
        if (u,p)==("admin","admin123"):
            st.session_state.logged_in=True; st.rerun()
        else: st.error("Wrong login")
    st.stop()

page=st.sidebar.radio("Menu",["Home","Students","Attendance","Marks","PDF Report"])
if st.sidebar.button("Logout"):
    st.session_state.logged_in=False; st.rerun()

try: students=db.execute("SELECT name,roll,course FROM students").fetchall()
except sqlite3.Error as e: st.error(str(e)); st.stop()

courses=["BCA","BBA","BSc","BCom","BA","BTech","MCA"]

if page=="Home":
    a,b,c=st.columns(3)
    a.metric("Students",len(students))
    b.metric("Attendance",db.execute("SELECT COUNT(*) FROM attendance").fetchone()[0])
    c.metric("Marks",db.execute("SELECT COUNT(*) FROM marks").fetchone()[0])

elif page=="Students":
    act=st.selectbox("Action",["View","Add","Edit","Delete"])
    if act=="Add":
        with st.form("add"):
            n=st.text_input("Name"); r=st.text_input("Roll")
            co=st.selectbox("Course",courses); ok=st.form_submit_button("Add")
        if ok:
            try:
                db.execute("INSERT INTO students(name,roll,course) VALUES(?,?,?)",(n.strip(),r.strip(),co))
                db.commit(); st.success("Added!"); st.rerun()
            except sqlite3.Error as e: st.error(str(e))
    elif act in ["Edit","Delete"] and students:
        s=st.selectbox("Student",students,format_func=lambda x:f"{x[0]} - {x[1]}")
        if act=="Edit":
            n=st.text_input("Name",s[0]); co=st.selectbox("Course",courses,index=courses.index(s[2]) if s[2] in courses else 0)
            if st.button("Update"):
                db.execute("UPDATE students SET name=?,course=? WHERE roll=?",(n,co,s[1]))
                db.commit(); st.rerun()
        elif st.button("Delete"):
            db.execute("DELETE FROM students WHERE roll=?",(s[1],)); db.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM students",db),use_container_width=True)

elif page in ["Attendance","Marks","PDF Report"]:
    if not students: st.info("Pehle student add karo.")
    else:
        s=st.selectbox("Student",students,format_func=lambda x:f"{x[0]} - {x[1]}")
        if page=="Attendance":
            d=st.date_input("Date"); status=st.selectbox("Status",["Present","Absent"])
            if st.button("Save Attendance"):
                db.execute("DELETE FROM attendance WHERE roll=? AND day=?",(s[1],str(d)))
                db.execute("INSERT INTO attendance VALUES(?,?,?)",(s[1],str(d),status))
                db.commit(); st.success("Saved!")
            rows=db.execute("SELECT day,status FROM attendance WHERE roll=?",(s[1],)).fetchall()
            st.dataframe(pd.DataFrame(rows,columns=["Date","Status"]),use_container_width=True)
            if rows: st.metric("Attendance %",f"{sum(x[1]=='Present' for x in rows)/len(rows)*100:.1f}%")
        elif page=="Marks":
            sub=st.text_input("Subject"); m=st.number_input("Marks",0,100)
            if st.button("Save Marks") and sub.strip():
                db.execute("DELETE FROM marks WHERE roll=? AND subject=?",(s[1],sub.strip()))
                db.execute("INSERT INTO marks VALUES(?,?,?)",(s[1],sub.strip(),m))
                db.commit(); st.success("Saved!")
            rows=db.execute("SELECT subject,marks FROM marks WHERE roll=?",(s[1],)).fetchall()
            st.dataframe(pd.DataFrame(rows,columns=["Subject","Marks"]),use_container_width=True)
            if rows: st.metric("Average",f"{sum(x[1] for x in rows)/len(rows):.1f}%")
        elif st.button("Generate PDF"):
            b=BytesIO(); pdf=canvas.Canvas(b)
            pdf.drawString(50,800,"COLLEGE REPORT")
            pdf.drawString(50,770,f"{s[0]} | {s[1]} | {s[2]}")
            for i,(sub,m) in enumerate(db.execute("SELECT subject,marks FROM marks WHERE roll=?",(s[1],)).fetchall()):
                pdf.drawString(50,730-i*25,f"{sub}: {m}/100")
            pdf.save()
            st.download_button("Download PDF",b.getvalue(),"report.pdf","application/pdf")

db.close()
