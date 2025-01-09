from flask import Flask, render_template, request, redirect, url_for, flash, g
import requests
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# SeaTable API tokens and base URLs
USERS_BASE_URL = "https://cloud.seatable.io/dtable/links/d4f3fdbdd6f043f389e0/api/v2.1"
USERS_TOKEN = "536656d47e2ceb91b121b0fc89fa3584b1e4a86a"

EXPENSES_BASE_URL = "https://cloud.seatable.io/dtable/links/e9795ec13a0f4b14a115/api/v2.1"
EXPENSES_TOKEN = "7577fdf485d2685c0aeeafa5ae6ab5da429288d5"

# Helper functions for interacting with SeaTable API
def fetch_table_data(base_url, token):
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(f"{base_url}/rows/", headers=headers)
    response.raise_for_status()
    return response.json()

def update_table_data(base_url, token, data):
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(f"{base_url}/batch-append-rows/", headers=headers, json=data)
    response.raise_for_status()

# Add before_request function here
@app.before_request
def before_request():
    """Sets the current_user globally based on the username passed."""
    g.current_user = request.args.get('username', None)

# Flask routes
@app.route('/')
def home():
    return render_template("home.html")

@app.route('/register', methods=["GET", "POST"])
def register_user():
    if request.method == "POST":
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for('register_user'))

        users_data = fetch_table_data(USERS_BASE_URL, USERS_TOKEN)

        if any(user['Username'] == username for user in users_data['rows']):
            flash("Username already exists!", "error")
            return redirect(url_for('register_user'))

        # Hash the password before storing
        hashed_password = generate_password_hash(password)

        # Add new user to SeaTable
        new_user = {"Username": username, "Password": hashed_password}
        update_table_data(USERS_BASE_URL, USERS_TOKEN, {"rows": [new_user]})

        flash("User registered successfully!", "success")
        return redirect(url_for('login_user'))

    return render_template('register.html')

@app.route('/login', methods=["GET", "POST"])
def login_user():
    if request.method == "POST":
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        users_data = fetch_table_data(USERS_BASE_URL, USERS_TOKEN)
        user = next((u for u in users_data['rows'] if u['Username'] == username), None)

        if not user or not check_password_hash(user['Password'], password):
            flash("Invalid username or password!", "error")
            return redirect(url_for('login_user'))

        flash(f"Welcome, {username}!", "success")
        return redirect(url_for('dashboard', username=username))

    return render_template('login.html')

@app.route('/dashboard/<username>', methods=["GET", "POST"])
def dashboard(username):
    if request.method == "POST":
        try:
            expense = float(request.form['expense'])
            reason = request.form['reason']
            income = float(request.form['income'] or 0)

            # Get the current date and time
            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Add new expense to SeaTable
            new_entry = {
                "Date": date,
                "Username": username,
                "Expense": expense,
                "Reason": reason,
                "Income": income
            }
            update_table_data(EXPENSES_BASE_URL, EXPENSES_TOKEN, {"rows": [new_entry]})

            flash("Expense recorded successfully!", "success")
        except ValueError:
            flash("Invalid input! Please ensure all fields are filled correctly.", "error")
        except Exception as e:
            flash(f"An error occurred: {e}", "error")

    # Fetch expenses for the current user
    expenses_data = fetch_table_data(EXPENSES_BASE_URL, EXPENSES_TOKEN)
    user_expenses = [e for e in expenses_data['rows'] if e['Username'] == username]
    return render_template('dashboard.html', username=username, expenses=user_expenses)

@app.route('/view_expenses/<username>')
def view_expenses(username):
    expenses_data = fetch_table_data(EXPENSES_BASE_URL, EXPENSES_TOKEN)
    user_expenses = [e for e in expenses_data['rows'] if e['Username'] == username]
    return render_template('view_expenses.html', expenses=user_expenses)

@app.route('/logout')
def logout():
    flash("You have logged out.", "info")
    return redirect(url_for('login_user'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
