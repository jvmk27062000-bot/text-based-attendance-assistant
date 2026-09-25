import React, { useEffect, useState } from "react";

const API = "http://127.0.0.1:5000";

function App() {
  const [command, setCommand] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [students, setStudents] = useState([]);
  const [summary, setSummary] = useState([]);
  const [records, setRecords] = useState([]);
  const [name, setName] = useState("");
  const [rollNo, setRollNo] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadData() {
    try {
      const [studentsRes, summaryRes, attendanceRes] = await Promise.all([
        fetch(`${API}/api/students`),
        fetch(`${API}/api/summary`),
        fetch(`${API}/api/attendance`),
      ]);

      if (!studentsRes.ok || !summaryRes.ok || !attendanceRes.ok) {
        throw new Error("Could not load dashboard data.");
      }

      setStudents(await studentsRes.json());
      setSummary(await summaryRes.json());
      setRecords(await attendanceRes.json());
    } catch (err) {
      setError(
        `${err.message} Make sure the Flask backend is running on port 5000.`
      );
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function submitAttendance(event) {
    event.preventDefault();
    setMessage("");
    setError("");

    if (!command.trim()) {
      setError("Enter an attendance message first.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API}/api/attendance/text`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: command }),
      });

      const data = await response.json();

      if (!response.ok) {
        const details = data.unmatched?.length
          ? ` Unmatched: ${data.unmatched.join(", ")}`
          : "";
        throw new Error((data.error || "Could not save attendance.") + details);
      }

      setMessage(
        `${data.message} ${data.students.join(", ")} marked ${data.status}.`
      );
      setCommand("");
      await loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function addStudent(event) {
    event.preventDefault();
    setMessage("");
    setError("");

    if (!name.trim()) {
      setError("Enter a student name.");
      return;
    }

    try {
      const response = await fetch(`${API}/api/students`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: name.trim(),
          roll_no: rollNo.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not add student.");
      }

      setMessage(`${data.name} was added to the roster.`);
      setName("");
      setRollNo("");
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <div className="container">
        <header className="hero">
          <p className="badge">NLP FULL-STACK MINI PROJECT</p>
          <h1>Text-Based Attendance Assistant</h1>
          <p>
            Type attendance naturally. The Flask NLP backend interprets it and
            stores the result in SQLite.
          </p>
        </header>

        {message && <div className="notice success">{message}</div>}
        {error && <div className="notice error">{error}</div>}

        <section className="card assistant">
          <h2>Mark Attendance with Text</h2>
          <p className="muted">
            Examples: “Ravi is present today”, “Manoj absent today”, or
            “Present: Ravi, Sita and John”
          </p>

          <form onSubmit={submitAttendance}>
            <textarea
              value={command}
              onChange={(event) => setCommand(event.target.value)}
              rows="4"
              placeholder="Type an attendance message..."
            />
            <button disabled={loading}>
              {loading ? "Processing..." : "Mark Attendance"}
            </button>
          </form>
        </section>

        <div className="grid two">
          <section className="card">
            <h2>Add Student</h2>

            <form onSubmit={addStudent} className="small-form">
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Student name"
              />

              <input
                value={rollNo}
                onChange={(event) => setRollNo(event.target.value)}
                placeholder="Roll number (optional)"
              />

              <button type="submit">Add Student</button>
            </form>
          </section>

          <section className="card">
            <h2>How it works</h2>
            <ol className="steps">
              <li>Enter natural-language attendance.</li>
              <li>Backend detects Present/Absent.</li>
              <li>Names are matched with the roster.</li>
              <li>Attendance is stored by date.</li>
            </ol>
          </section>
        </div>

        <section className="card">
          <div className="section-title">
            <h2>Attendance Summary</h2>
            <span>{students.length} students</span>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Roll No.</th>
                  <th>Present</th>
                  <th>Absent</th>
                  <th>Marked</th>
                  <th>Attendance %</th>
                </tr>
              </thead>
              <tbody>
                {summary.map((student) => (
                  <tr key={student.id}>
                    <td>{student.name}</td>
                    <td>{student.roll_no || "-"}</td>
                    <td>{student.present_count}</td>
                    <td>{student.absent_count}</td>
                    <td>{student.total_marked}</td>
                    <td>
                      <span className="percent">
                        {student.percentage.toFixed(2)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card">
          <div className="section-title">
            <h2>Recent Attendance Records</h2>
            <span>{records.length} records</span>
          </div>

          {records.length === 0 ? (
            <p className="muted">
              No attendance records yet. Enter a message above to create one.
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Student</th>
                    <th>Roll No.</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {records.slice(0, 20).map((record) => (
                    <tr key={record.id}>
                      <td>{record.attendance_date}</td>
                      <td>{record.name}</td>
                      <td>{record.roll_no || "-"}</td>
                      <td>
                        <span className={`status ${record.status}`}>
                          {record.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default App;
