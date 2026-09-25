from datetime import date
from pathlib import Path
import re
import sqlite3

from flask import Flask, jsonify, request
from flask_cors import CORS
from rapidfuzz import process, fuzz

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "attendance.db"

app = Flask(__name__)
CORS(app)
@app.get("/")
def home():
    return jsonify({"message": "Backend is live!", "status": "ok"})


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            roll_no TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('present', 'absent')),
            UNIQUE(student_id, attendance_date),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    demo_students = [
        ("Manoj", "23A01"),
        ("Ravi", "23A02"),
        ("Sita", "23A03"),
        ("John", "23A04"),
        ("NKR", "23A05"),
    ]

    for name, roll_no in demo_students:
        conn.execute(
            "INSERT OR IGNORE INTO students(name, roll_no) VALUES (?, ?)",
            (name, roll_no),
        )

    conn.commit()
    conn.close()


def normalize_text(text):
    return re.sub(r"\s+", " ", text.strip().lower())


def detect_status(text):
    text = normalize_text(text)

    absent_words = [
        "absent",
        "not present",
        "wasn't present",
        "was not present",
        "are absent",
        "were absent",
    ]

    present_words = [
        "present",
        "attended",
        "is present",
        "are present",
        "was present",
        "were present",
    ]

    for phrase in absent_words:
        if phrase in text:
            return "absent"

    for phrase in present_words:
        if phrase in text:
            return "present"

    return None


def clean_name_fragment(fragment):
    fragment = fragment.strip(" .,:;!?")
    fragment = re.sub(
        r"\b(today|yesterday|present|absent|was|were|is|are|student|students)\b",
        "",
        fragment,
        flags=re.IGNORECASE,
    )
    return fragment.strip(" .,:;!?-")


def split_names(text):
    """
    Extract a simple list of possible student names from a sentence.
    Handles:
      Ravi
      Ravi and Manoj
      Ravi, Sita and John
      Present: Ravi, Sita
      Ravi was absent
    """
    working = normalize_text(text)

    # Remove common attendance phrases.
    working = re.sub(
        r"\b(today|present|absent|attended|wasn't present|was not present|"
        r"were absent|are absent|is absent|was absent|were present|"
        r"are present|is present|was present)\b",
        " ",
        working,
    )

    # Remove common sentence scaffolding.
    working = re.sub(
        r"\b(were|was|is|are|be|students?|please|mark|marks|attendance|"
        r"attendance for|as|today)\b",
        " ",
        working,
    )

    working = working.replace(";", ",")
    working = re.sub(r"\s+", " ", working).strip(" ,")

    # Convert "and" to commas for simple list parsing.
    working = re.sub(r"\s+\band\b\s+", ",", working)

    pieces = [clean_name_fragment(x) for x in working.split(",")]
    pieces = [x for x in pieces if x]

    # Only keep short name-like fragments.
    results = []
    for piece in pieces:
        piece = re.sub(r"\s+", " ", piece)
        if len(piece.split()) <= 3:
            results.append(piece)

    return results


def fetch_students():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, roll_no FROM students ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def match_students(fragments):
    students = fetch_students()
    choices = [s["name"] for s in students]
    matches = []
    unmatched = []

    for fragment in fragments:
        if not fragment:
            continue

        # Exact case-insensitive matching first.
        exact = next(
            (s for s in students if s["name"].lower() == fragment.lower()),
            None,
        )

        if exact:
            matches.append(exact)
            continue

        # Fuzzy matching against roster.
        result = process.extractOne(
            fragment,
            choices,
            scorer=fuzz.WRatio,
            score_cutoff=80,
        )

        if result:
            matched_name = result[0]
            student = next(
                s for s in students if s["name"] == matched_name
            )
            matches.append(student)
        else:
            unmatched.append(fragment)

    # De-duplicate matched students.
    unique = {}
    for student in matches:
        unique[student["id"]] = student

    return list(unique.values()), unmatched


def save_attendance(students, status, attendance_date):
    conn = get_db()
    saved = []

    for student in students:
        # Upsert today's attendance status.
        conn.execute(
            """
            INSERT INTO attendance(student_id, attendance_date, status)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id, attendance_date)
            DO UPDATE SET status = excluded.status
            """,
            (student["id"], attendance_date, status),
        )
        saved.append(student["name"])

    conn.commit()
    conn.close()
    return saved


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/students")
def get_students():
    return jsonify(fetch_students())


@app.post("/api/students")
def add_student():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    roll_no = str(data.get("roll_no", "")).strip()

    if not name:
        return jsonify({"error": "Student name is required."}), 400

    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO students(name, roll_no) VALUES (?, ?)",
            (name, roll_no or None),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "A student with that name already exists."}), 409

    student_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "id": student_id,
        "name": name,
        "roll_no": roll_no,
    }), 201


@app.post("/api/attendance/text")
def attendance_from_text():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()

    if not text:
        return jsonify({"error": "Please enter an attendance message."}), 400

    status = detect_status(text)

    if not status:
        return jsonify({
            "error": "I could not detect Present or Absent in the message.",
            "examples": [
                "Ravi is present today",
                "Manoj absent today",
                "Present: Ravi, Sita and John",
            ],
        }), 422

    fragments = split_names(text)
    students, unmatched = match_students(fragments)

    if not students:
        return jsonify({
            "error": "I could not match any student names from the message.",
            "detected_fragments": fragments,
            "unmatched": unmatched,
        }), 422

    attendance_date = date.today().isoformat()
    saved = save_attendance(students, status, attendance_date)

    return jsonify({
        "message": "Attendance recorded successfully.",
        "date": attendance_date,
        "status": status,
        "students": saved,
        "unmatched": unmatched,
    })


@app.get("/api/attendance")
def get_attendance():
    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            attendance.id,
            students.name,
            students.roll_no,
            attendance.attendance_date,
            attendance.status
        FROM attendance
        JOIN students ON students.id = attendance.student_id
        ORDER BY attendance.attendance_date DESC, students.name ASC
        """
    ).fetchall()

    conn.close()
    return jsonify([dict(row) for row in rows])


@app.get("/api/summary")
def get_summary():
    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            students.id,
            students.name,
            students.roll_no,
            COUNT(attendance.id) AS total_marked,
            COALESCE(
                SUM(CASE WHEN attendance.status = 'present' THEN 1 ELSE 0 END),
                0
            ) AS present_count,
            COALESCE(
                SUM(CASE WHEN attendance.status = 'absent' THEN 1 ELSE 0 END),
                0
            ) AS absent_count
        FROM students
        LEFT JOIN attendance ON attendance.student_id = students.id
        GROUP BY students.id
        ORDER BY students.name
        """
    ).fetchall()

    conn.close()

    output = []

    for row in rows:
        total = row["total_marked"]
        present = row["present_count"]
        percentage = (present / total * 100) if total else 0

        output.append({
            "id": row["id"],
            "name": row["name"],
            "roll_no": row["roll_no"],
            "total_marked": total,
            "present_count": present,
            "absent_count": row["absent_count"],
            "percentage": round(percentage, 2),
        })

    return jsonify(output)


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
