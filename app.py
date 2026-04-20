from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import datetime
import qrcode
import os
# create database automatically if not exists
if not os.path.exists("database.db"):
    import database
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "pharmacare_secret"

# create qr folder
if not os.path.exists("qr_codes"):
    os.makedirs("qr_codes")


# 🔍 expiry check
def check_expiry(expiry_date):
    today = datetime.today().date()
    expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
    days_left = (expiry - today).days

    if days_left < 0:
        return "Expired"
    elif days_left <= 7:
        return "Expiring Soon"
    else:
        return "Safe"


# 🔐 login required
def login_required(func):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# 🔥 login first
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("index.html")


# 🔐 signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template("signup.html")


# 🔐 login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect(url_for('home'))
        else:
            return "Invalid Credentials"

    return render_template("login.html")


# 🔓 logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


# ➕ add medicine
@app.route('/add', methods=['POST'])
@login_required
def add():
    name = request.form['name']
    batch = request.form['batch']
    expiry = request.form['expiry']
    location = request.form['location']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO medicine (name, batch, expiry, location) VALUES (?, ?, ?, ?)",
        (name, batch, expiry, location)
    )
    conn.commit()

    med_id = cursor.lastrowid
    conn.close()

    # qr
    qr_data = f"ID:{med_id}, Name:{name}, Batch:{batch}, Expiry:{expiry}, Location:{location}"
    img = qrcode.make(qr_data)
    img.save(f"qr_codes/medicine_{med_id}.png")

    return redirect(url_for('inventory'))


# 📦 inventory
@app.route('/inventory')
@login_required
def inventory():
    conn = sqlite3.connect('database.db')
    data = conn.execute("SELECT * FROM medicine").fetchall()
    conn.close()

    medicines = []
    for med in data:
        expiry = med[3] if med[3] else "2000-01-01"
        status = check_expiry(expiry)

        medicines.append([med[0], med[1], med[2], expiry, med[4], status])

    return render_template("view.html", medicines=medicines)


# 📊 dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('database.db')
    data = conn.execute("SELECT * FROM medicine").fetchall()
    conn.close()

    total = len(data)
    expired = 0
    expiring = 0

    for med in data:
        expiry = med[3] if med[3] else "2000-01-01"
        status = check_expiry(expiry)

        if status == "Expired":
            expired += 1
        elif status == "Expiring Soon":
            expiring += 1

    return render_template("dashboard.html",
                           total=total,
                           expired=expired,
                           expiring=expiring)


# 🔍 search
@app.route('/search', methods=['POST'])
@login_required
def search():
    name = request.form['name']

    conn = sqlite3.connect('database.db')
    data = conn.execute(
        "SELECT * FROM medicine WHERE name LIKE ?",
        ('%' + name + '%',)
    ).fetchall()
    conn.close()

    medicines = []
    for med in data:
        expiry = med[3] if med[3] else "2000-01-01"
        status = check_expiry(expiry)

        medicines.append([med[0], med[1], med[2], expiry, med[4], status])

    return render_template("view.html", medicines=medicines)


# 📷 scan page
@app.route('/scan')
@login_required
def scan():
    return render_template("scan.html")


# 📷 scan result
@app.route('/scan_result/<path:data>')
@login_required
def scan_result(data):
    try:
        med_id = int(data.split(",")[0].split(":")[1])

        conn = sqlite3.connect('database.db')
        result = conn.execute(
            "SELECT * FROM medicine WHERE id=?", (med_id,)
        ).fetchall()
        conn.close()

        medicines = []
        for med in result:
            expiry = med[3] if med[3] else "2000-01-01"
            status = check_expiry(expiry)

            medicines.append([med[0], med[1], med[2], expiry, med[4], status])

        return render_template("view.html", medicines=medicines)

    except:
        return "Invalid QR Code"


# 🔔 alerts
@app.route('/check_alerts')
@login_required
def check_alerts():
    conn = sqlite3.connect('database.db')
    data = conn.execute("SELECT * FROM medicine").fetchall()
    conn.close()

    expired = 0
    expiring = 0

    for med in data:
        expiry = med[3] if med[3] else "2000-01-01"
        status = check_expiry(expiry)

        if status == "Expired":
            expired += 1
        elif status == "Expiring Soon":
            expiring += 1

    return jsonify({"expired": expired, "expiring": expiring})


# 🚀 RUN APP
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
