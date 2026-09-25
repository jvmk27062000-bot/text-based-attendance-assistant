# Text-Based Attendance Assistant

A full-stack NLP mini project for recording student attendance using natural-language text.

## Stack

- Frontend: React + Vite
- Backend: Python Flask
- NLP: rule-based text parsing + fuzzy student-name matching
- Database: SQLite

## Example commands

Type commands such as:

```text
Ravi is present today
Manoj absent today
Present: Ravi, Sita and John
Ravi and Manoj were absent today
```

The backend extracts student names and the attendance state, saves the attendance date, and returns updated attendance statistics.

## Folder structure

```text
text-attendance-assistant/
├── backend/
│   ├── app.py
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       └── style.css
└── README.md
```

## 1. Start the backend

Open a terminal:

```bash
cd backend
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Flask:

```bash
python app.py
```

The API runs at:

```text
http://127.0.0.1:5000
```

The SQLite database file is created automatically as:

```text
backend/attendance.db
```

## 2. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL shown by Vite, normally:

```text
http://localhost:5173
```

## 3. First use

The backend creates a demo roster automatically:

- Manoj
- Ravi
- Sita
- John
- NKR

You can add more students from the web page.

## API endpoints

### GET `/api/students`

Returns the student roster.

### POST `/api/students`

Request:

```json
{
  "name": "Kiran",
  "roll_no": "23A01"
}
```

### POST `/api/attendance/text`

Request:

```json
{
  "text": "Ravi and Manoj were absent today"
}
```

The server detects:

- student names
- present/absent status
- attendance date

### GET `/api/attendance`

Returns saved attendance records.

### GET `/api/summary`

Returns attendance percentages per student.

## How NLP parsing works

This educational project uses a transparent NLP pipeline:

```text
User text
   ↓
Normalize text
   ↓
Detect attendance keyword
   ↓
Split possible student names
   ↓
Match names against roster
   ↓
Store attendance
   ↓
Return result to React
```

The application intentionally uses a controlled roster instead of guessing arbitrary people from text.
