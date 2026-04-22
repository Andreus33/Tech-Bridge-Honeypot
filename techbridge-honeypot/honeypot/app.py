"""
TechBridge Academy — Educational Honeypot
For cybersecurity research and education only.
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, send_from_directory
)
import sqlite3, os, logging, json
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "techbridge-honeypot-secret-2024"

# ── Logging setup ──────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

activity_logger = logging.getLogger("honeypot")
activity_logger.setLevel(logging.INFO)
fh = logging.FileHandler("logs/activity.log")
fh.setFormatter(logging.Formatter("%(message)s"))
activity_logger.addHandler(fh)

def log_event(action, details="", username="anonymous"):
    ip        = request.remote_addr or "unknown"
    ts        = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    user      = username or session.get("username", "anonymous")
    entry     = f"{ts} | {ip} | {user} | {action} | {details}"
    activity_logger.info(entry)
    print(entry)          # also echo to console during dev

# ── Database ───────────────────────────────────────────────────────────────────
def get_db():
    db = sqlite3.connect("database.db")
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS students (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email    TEXT NOT NULL,
            password TEXT NOT NULL,
            course   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS courses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name     TEXT NOT NULL,
            course_material TEXT NOT NULL,
            video           TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS access_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT NOT NULL,
            ip         TEXT NOT NULL,
            username   TEXT NOT NULL,
            action     TEXT NOT NULL,
            details    TEXT
        );
    """)

    # Seed users
    users = [
        ("student1",   "password123",    "student"),
        ("student2",   "qwerty123",      "student"),
        ("student3",   "letmein456",     "student"),
        ("admin",      "admin",          "admin"),
        ("superadmin", "SuperSecret123", "superadmin"),
    ]
    for u, p, r in users:
        try:
            db.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)", (u,p,r))
        except sqlite3.IntegrityError:
            pass

    # Seed student records (intentionally "exposed" in admin panel — deception data)
    students = [
        ("student1", "student1@techbridge.edu", "password123",  "AWS Fundamentals"),
        ("student2", "student2@techbridge.edu", "qwerty123",    "Cybersecurity Fundamentals"),
        ("student3", "student3@techbridge.edu", "letmein456",   "AWS Fundamentals"),
        ("jdoe",     "jdoe@techbridge.edu",     "john2024!",    "Cybersecurity Fundamentals"),
        ("msmith",   "msmith@techbridge.edu",   "Summer2024#",  "AWS Fundamentals"),
    ]
    for s in students:
        try:
            db.execute("INSERT INTO students (username,email,password,course) VALUES (?,?,?,?)", s)
        except Exception:
            pass

    # Seed courses
    courses = [
        ("AWS Fundamentals",
         "AWS_Intro.pdf,EC2_Overview.pdf,VPC_Networking.pdf",
         "aws_intro.mp4,ec2_setup.mp4"),
        ("Cybersecurity Fundamentals",
         "Security_Basics.pdf,Network_Security.pdf,Incident_Response.pdf",
         "cyber_intro.mp4,incident_response.mp4"),
    ]
    for c in courses:
        try:
            db.execute("INSERT INTO courses (course_name,course_material,video) VALUES (?,?,?)", c)
        except Exception:
            pass

    db.commit()
    db.close()

def log_to_db(action, details=""):
    try:
        db = get_db()
        db.execute(
            "INSERT INTO access_log (timestamp,ip,username,action,details) VALUES (?,?,?,?,?)",
            (datetime.utcnow().isoformat(),
             request.remote_addr,
             session.get("username","anonymous"),
             action, details)
        )
        db.commit()
        db.close()
    except Exception:
        pass

# ── Auth helpers ───────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get("role") not in roles:
                log_event("UNAUTHORIZED_ACCESS",
                          f"Required roles: {roles}, got: {session.get('role')}")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()

        db   = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        db.close()

        if user:
            session["username"] = user["username"]
            session["role"]     = user["role"]
            log_event("LOGIN_SUCCESS", f"role={user['role']}", username)
            log_to_db("LOGIN_SUCCESS", f"role={user['role']}")

            if user["role"] == "student":
                return redirect(url_for("student_dashboard"))
            elif user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user["role"] == "superadmin":
                return redirect(url_for("terminal"))
        else:
            log_event("LOGIN_FAILED", f"bad credentials for '{username}'", username)
            log_to_db("LOGIN_FAILED", f"attempted username={username}")
            error = "Invalid credentials. Please try again."

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    log_event("LOGOUT", "session ended")
    session.clear()
    return redirect(url_for("login"))

# ── Student ────────────────────────────────────────────────────────────────────

@app.route("/student")
@login_required
@role_required("student")
def student_dashboard():
    db      = get_db()
    courses = db.execute("SELECT * FROM courses").fetchall()
    db.close()
    log_event("PAGE_VIEW", "student dashboard")
    return render_template("student_dashboard.html",
                           username=session["username"],
                           courses=courses)

@app.route("/course/<int:course_id>")
@login_required
@role_required("student")
def course_detail(course_id):
    db     = get_db()
    course = db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    db.close()
    if not course:
        return redirect(url_for("student_dashboard"))
    materials = [m.strip() for m in course["course_material"].split(",")]
    videos    = [v.strip() for v in course["video"].split(",")]
    log_event("COURSE_VIEW", f"course_id={course_id} name={course['course_name']}")
    return render_template("course_detail.html",
                           username=session["username"],
                           course=course,
                           materials=materials,
                           videos=videos)

# ── Admin ──────────────────────────────────────────────────────────────────────

@app.route("/admin")
@login_required
@role_required("admin","superadmin")
def admin_dashboard():
    db       = get_db()
    students = db.execute("SELECT * FROM students").fetchall()
    courses  = db.execute("SELECT * FROM courses").fetchall()
    logs     = db.execute(
        "SELECT * FROM access_log ORDER BY id DESC LIMIT 50"
    ).fetchall()
    db.close()
    log_event("PAGE_VIEW", "admin dashboard")
    return render_template("admin_dashboard.html",
                           username=session["username"],
                           students=students,
                           courses=courses,
                           logs=logs)

@app.route("/admin/passwords")
@login_required
@role_required("admin","superadmin")
def passwords_file():
    """
    Honeypot lure: intentionally exposes a 'passwords.txt' that contains
    fake credentials. Access is silently logged for research purposes.
    """
    log_event("SENSITIVE_FILE_ACCESS",
              "passwords.txt accessed — HIGH INTEREST EVENT",
              session.get("username"))
    log_to_db("PASSWORDS_FILE_ACCESS", "honeypot trigger: passwords.txt")

    content = """# TechBridge Academy — Credential Store
# Last updated: 2024-01-15
# NOTE: Migrate to vault ASAP (IT ticket #4821)

superadmin:SuperSecret123
admin:admin
student1:password123
student2:qwerty123
student3:letmein456
jdoe:john2024!
msmith:Summer2024#
dbuser:db_pass_2023
backup_svc:Backup$ecure99
"""
    return app.response_class(content, mimetype="text/plain",
                              headers={"Content-Disposition":
                                       "attachment; filename=passwords.txt"})

# ── Super Admin Terminal ───────────────────────────────────────────────────────

@app.route("/terminal")
@login_required
@role_required("superadmin")
def terminal():
    log_event("TERMINAL_ACCESS", "superadmin terminal opened")
    return render_template("terminal.html", username=session["username"])

@app.route("/api/terminal", methods=["POST"])
@login_required
@role_required("superadmin")
def terminal_api():
    data    = request.get_json(silent=True) or {}
    command = data.get("command","").strip()
    log_event("TERMINAL_COMMAND", f"cmd='{command}'")
    log_to_db("TERMINAL_COMMAND", command)

    response = process_command(command)
    return jsonify({"output": response, "command": command})

def process_command(cmd):
    parts = cmd.split()
    if not parts:
        return ""
    base = parts[0]

    if base == "ls":
        path = parts[1] if len(parts) > 1 else "."
        if "AWS" in path or "aws" in path:
            return "AWS_Intro.pdf\nEC2_Overview.pdf\nVPC_Networking.pdf\naws_intro.mp4\nec2_setup.mp4"
        elif "Cyber" in path or "cyber" in path or "security" in path.lower():
            return "Security_Basics.pdf\nNetwork_Security.pdf\nIncident_Response.pdf\ncyber_intro.mp4\nincident_response.mp4"
        else:
            return ("courses/\nfake_files/\nlogs/\napp.py\ndatabase.db\nrequirements.txt\n"
                    "AWS_Intro.pdf\nEC2_Overview.pdf\nVPC_Networking.pdf\nVPC_Networking.pdf\n"
                    "aws_intro.mp4\nec2_setup.mp4\nSecurity_Basics.pdf\nNetwork_Security.pdf\n"
                    "Incident_Response.pdf\ncyber_intro.mp4\nincident_response.mp4")

    elif base == "pwd":
        return "/home/admin/courses"

    elif base == "whoami":
        return "root"

    elif base == "id":
        return "uid=0(root) gid=0(root) groups=0(root)"

    elif base == "uname":
        return "Linux techbridge-prod 5.4.0-182-generic #202-Ubuntu SMP x86_64 GNU/Linux"

    elif base == "cat":
        fname = parts[1] if len(parts) > 1 else ""
        log_event("FILE_READ_ATTEMPT", f"file={fname}")
        if "passwd" in fname or "shadow" in fname:
            log_event("SENSITIVE_READ", f"CRITICAL: attempted to read {fname}")
            return ("root:x:0:0:root:/root:/bin/bash\n"
                    "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
                    "admin:x:1000:1000:,,,:/home/admin:/bin/bash\n"
                    "student:x:1001:1001:,,,:/home/student:/bin/bash")
        return f"cat: {fname}: Permission denied"

    elif base == "cd":
        return ""   # silent, like a real shell

    elif base == "clear":
        return "__CLEAR__"

    elif base == "history":
        return ("1  ls\n2  cd courses\n3  ls -la\n4  cat /etc/passwd\n"
                "5  wget http://internal-backup/db_dump.sql\n6  history")

    elif base == "ps":
        return ("PID TTY          TIME CMD\n"
                "  1 ?        00:00:01 systemd\n"
                "582 ?        00:00:00 sshd\n"
                "901 pts/0    00:00:00 bash\n"
                "923 pts/0    00:00:00 flask\n"
                "950 pts/0    00:00:00 ps")

    elif base == "ifconfig" or base == "ip":
        return ("eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
                "        inet 10.0.1.42  netmask 255.255.255.0  broadcast 10.0.1.255\n"
                "        inet6 fe80::215:5dff:fe01:1  prefixlen 64\n"
                "        ether 00:15:5d:00:00:01  txqueuelen 1000")

    elif base in ("wget","curl"):
        url = parts[1] if len(parts) > 1 else ""
        log_event("NETWORK_ATTEMPT", f"CRITICAL: {base} {url}")
        return f"--2024-01-15 09:23:41--  {url}\nResolving {url.split('/')[2] if '//' in url else url}... failed: Name or service not known."

    elif base == "sudo":
        log_event("PRIVILEGE_ESCALATION_ATTEMPT", f"sudo cmd: {' '.join(parts[1:])}")
        return "[sudo] password for admin: \nSorry, try again."

    elif base == "python" or base == "python3":
        return "Python 3.8.10 (default, Nov 14 2022, 12:59:47)\n[GCC 9.4.0] on linux\nType 'help' for more info."

    elif base == "help":
        return ("Available commands: ls, pwd, whoami, id, uname, cat, cd, clear,\n"
                "history, ps, ifconfig, ip, wget, curl, sudo, python, python3, help, exit")

    elif base == "exit":
        return "__EXIT__"

    else:
        return f"bash: {base}: command not found"

# ── File download (canary trap) ────────────────────────────────────────────────

@app.route("/download/<path:filename>")
@login_required
def download_file(filename):
    log_event("FILE_DOWNLOAD", f"CANARY TRIGGERED: file={filename}")
    log_to_db("FILE_DOWNLOAD", f"canary={filename}")
    # Serve from fake_files directory (harmless placeholder files)
    safe_dir = os.path.join(app.root_path, "fake_files")
    return send_from_directory(safe_dir, filename, as_attachment=True)

# ── API: recent logs for admin ─────────────────────────────────────────────────

@app.route("/api/logs")
@login_required
@role_required("admin","superadmin")
def api_logs():
    db   = get_db()
    rows = db.execute(
        "SELECT * FROM access_log ORDER BY id DESC LIMIT 100"
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("\n" + "="*55)
    print("  TechBridge Academy Honeypot")
    print("  http://127.0.0.1:5000")
    print("="*55)
    print("  student1 / password123  → Student Portal")
    print("  admin    / admin        → Admin Dashboard")
    print("  superadmin / SuperSecret123 → Terminal")
    print("="*55 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
