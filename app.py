from flask import Flask, render_template, request, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "servicecare_secret_key"


# Database connection
def get_db_connection():
    conn = sqlite3.connect("service.db")
    conn.row_factory = sqlite3.Row
    return conn


# Create database tables
def create_tables():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS service_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# Home page
@app.route('/')
def home():
    return render_template('index.html')


# Service request page
@app.route('/request')
def service_request():
    return render_template('request.html')


# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']

        password_hash = generate_password_hash(password)

        conn = get_db_connection()

        try:
            conn.execute("""
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
            """, (name, email, password_hash))

            conn.commit()
            message = "Registration Successful!"

        except sqlite3.IntegrityError:
            message = "This email is already registered."

        finally:
            conn.close()

        return f"""
        <h2>{message}</h2>
        <a href="/login">Go to Login</a>
        """

    return render_template('register.html')


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']

            return render_template('login_success.html')

        return render_template('login_error.html')

    return render_template('login.html')


# Submit service request
@app.route('/submit_request', methods=['POST'])
def submit_request():

    if 'user_id' not in session:
        return render_template('login_required.html')

    category = request.form['service']
    description = request.form['description']

    user_id = session['user_id']

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO service_requests
        (user_id, category, description)
        VALUES (?, ?, ?)
    """, (user_id, category, description))

    conn.commit()
    conn.close()

    return render_template('request_success.html')
# Temporary password reset
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        new_password = request.form['password']

        password_hash = generate_password_hash(new_password)

        conn = get_db_connection()

        result = conn.execute("""
            UPDATE users
            SET password_hash = ?
            WHERE email = ?
        """, (password_hash, email))

        conn.commit()
        updated = result.rowcount
        conn.close()

        if updated > 0:
            return "<h2>Password Reset Successful!</h2><a href='/login'>Login Now</a>"

        return "<h2>Email not found!</h2><a href='/reset_password'>Try Again</a>"

    return """
    <h2>Reset Password</h2>
    <form method="POST">
        <input type="email" name="email" placeholder="Registered Email" required>
        <input type="password" name="password" placeholder="New Password" minlength="8" required>
        <button type="submit">Reset Password</button>
    </form>
    """

# My Requests page
@app.route('/my_requests')
def my_requests():

    if 'user_id' not in session:
        return render_template('login_required.html')

    user_id = session['user_id']

    conn = get_db_connection()

    requests_list = conn.execute("""
        SELECT * FROM service_requests
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,)).fetchall()

    conn.close()

    return render_template(
        'my_requests.html',
        requests_list=requests_list
    )

# Admin Login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        if email == "admin@servicecare.com" and password == "Admin@123":

            session['admin'] = True

            return """
            <h2>Admin Login Successful!</h2>
            <p>Welcome to ServiceCare Admin Panel.</p>
            <a href="/admin_dashboard">Open Dashboard</a>
            """

        return """
        <h2>Invalid Admin Email or Password!</h2>
        <a href="/admin_login">Try Again</a>
        """

    return render_template('admin_login.html')

# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():

    if 'admin' not in session:
        return """
        <h2>Access Denied!</h2>
        <a href="/admin_login">Admin Login</a>
        """

    conn = get_db_connection()

    all_requests = conn.execute("""
        SELECT
            service_requests.id,
            users.name,
            users.email,
            service_requests.category,
            service_requests.description,
            service_requests.status
        FROM service_requests
        LEFT JOIN users
        ON service_requests.user_id = users.id
        ORDER BY service_requests.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        'admin_dashboard.html',
        all_requests=all_requests
    )

# Update Service Request Status
@app.route('/update_status/<int:request_id>', methods=['POST'])
def update_status(request_id):

    if 'admin' not in session:
        return """
        <h2>Access Denied!</h2>
        <a href="/admin_login">Admin Login</a>
        """

    new_status = request.form['status']

    allowed_statuses = ['Pending', 'In Progress', 'Completed']

    if new_status not in allowed_statuses:
        return "Invalid Status!"

    conn = get_db_connection()

    conn.execute("""
        UPDATE service_requests
        SET status = ?
        WHERE id = ?
    """, (new_status, request_id))

    conn.commit()
    conn.close()

    return """
    <h2>Request Status Updated Successfully!</h2>
    <a href="/admin_dashboard">Back to Dashboard</a>
    """
# About Page
@app.route('/about')
def about():
    return render_template('about.html')


# Services Page
@app.route('/services')
def services():
    return render_template('services.html')

# User Logout
@app.route('/logout')
@app.route('/logout')
def logout():
    session.clear()
    return render_template('logout.html')


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)