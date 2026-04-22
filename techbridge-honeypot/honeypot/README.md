# TechBridge Academy — Educational Honeypot

> **Educational Disclaimer:** This project is created for cybersecurity education and
> honeypot simulation purposes only. Deploy only in controlled environments you own
> or have explicit written permission to test. Never deploy against real users without
> informed consent.

---

## Overview

A realistic Learning Management System (LMS) honeypot built with Python Flask, SQLite,
and vanilla HTML/CSS/JS. It silently logs all attacker interactions — logins, file access,
terminal commands, credential harvesting attempts — to a structured log file and SQLite
database. No confrontational popups; all observation is passive, like a real honeypot.

### Architecture

```
Attacker visits login → tries credentials
  ├── student1 / password123  → Student Portal (realistic LMS dashboard)
  ├── admin    / admin         → Admin Panel (exposes "credential" lure + canary files)
  └── superadmin / SuperSecret123 → Fake Ubuntu 20.04 terminal
```

Every action is logged to:
- `logs/activity.log`  (flat file, human-readable)
- `database.db` → `access_log` table (queryable)

---

## Setup

### Requirements
- Python 3.8+

### Install

```bash
pip install -r requirements.txt
python app.py
```

Then open: **http://127.0.0.1:5000**

---

## Demo Credentials

| Username    | Password        | Role       | Lands On           |
|-------------|-----------------|------------|--------------------|
| student1    | password123     | student    | Student Dashboard  |
| admin       | admin           | admin      | Admin Panel        |
| superadmin  | SuperSecret123  | superadmin | Ubuntu Terminal    |

---

## Honeypot Mechanisms

### 1. Login Logging
Every login attempt (success and failure) is logged with timestamp, IP, and username.

### 2. Credential Lure (Admin Panel)
The admin dashboard displays a student records table with plaintext passwords and
a banner referencing a `passwords.txt` file. Accessing `/admin/passwords` triggers
a `PASSWORDS_FILE_ACCESS` log event — a high-interest signal that an attacker is
harvesting credentials.

### 3. Canary File Downloads
All "course files" (PDFs, MP4s) are harmless text placeholders. Any download attempt
triggers a `FILE_DOWNLOAD / CANARY TRIGGERED` event logged with IP, username, and filename.

### 4. Terminal Command Logging
The superadmin Ubuntu terminal logs every command. High-interest commands like
`wget`, `curl`, `cat /etc/passwd`, and `sudo` generate elevated log entries.

### 5. Silent Observation
Nothing tells the visitor they are being watched. This is how production honeypots
(Cowrie, OpenCanary, etc.) operate — passive observation, not confrontation.

---

## Log Format

```
2024-01-15 09:23:41 UTC | 192.168.1.10 | admin | LOGIN_SUCCESS | role=admin
2024-01-15 09:24:05 UTC | 192.168.1.10 | admin | PASSWORDS_FILE_ACCESS | honeypot trigger: passwords.txt
2024-01-15 09:24:18 UTC | 192.168.1.10 | admin | FILE_DOWNLOAD | CANARY TRIGGERED: file=AWS_Intro.pdf
2024-01-15 09:31:02 UTC | 192.168.1.10 | superadmin | TERMINAL_COMMAND | cmd='cat /etc/passwd'
2024-01-15 09:31:04 UTC | 192.168.1.10 | superadmin | SENSITIVE_READ | CRITICAL: attempted to read /etc/passwd
```

---

## File Structure

```
honeypot/
├── app.py                    ← Flask application + all routes
├── database.db               ← SQLite (auto-created on first run)
├── requirements.txt
├── README.md
├── templates/
│   ├── login.html            ← Login page
│   ├── student_dashboard.html
│   ├── course_detail.html
│   ├── admin_dashboard.html  ← Credential lure + canary file list
│   └── terminal.html         ← Fake Ubuntu terminal UI
├── static/
│   └── js/terminal.js        ← Terminal interaction (no client alerts)
├── fake_files/               ← Harmless canary placeholder files
│   ├── AWS_Intro.pdf
│   ├── EC2_Overview.pdf
│   └── ...
└── logs/
    └── activity.log          ← Human-readable event log
```

---

## Production Notes

- Set `app.secret_key` to a strong random value before deploying
- Run behind a reverse proxy (nginx) for real-world use
- Consider adding GeoIP lookups to enrich log data
- Integrate with a SIEM (Splunk, ELK) by tailing `logs/activity.log`
- For internet-facing deployment, use a dedicated VM / cloud instance
