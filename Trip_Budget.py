import socket
import psycopg2
import random
import string
from datetime import datetime
import urllib.parse
import os
import time
import hashlib
from http.cookies import SimpleCookie
import hashlib

SESSION_DURATION = 3600  # 1 hour

sessions = {}

def generate_session_id():
    """Generate a new session ID."""
    session_id = hashlib.sha256(os.urandom(16)).hexdigest()
    return session_id

def create_session(username):
    """Create a new session for the user."""
    session_id = generate_session_id()
    sessions[session_id] = {
        'username': username,
        'last_active': time.time()
    }
    return session_id


def get_session(session_id):
    """Get the session data for the given session ID."""
    if session_id in sessions:
        session_data = sessions[session_id]
        session_data['last_active'] = time.time()  
        return session_data
    return None

def check_session(session_id):
    """Check if the session is valid and not expired."""
    session_data = get_session(session_id)
    if session_data:
        last_active = session_data['last_active']
        if time.time() - last_active < SESSION_DURATION:
            return True
    return False

# Simulate a valid session
# valid_session_id = create_session("test_user")
# print("Checking a valid session:")
# print("Session is valid:", check_session(valid_session_id))

# # Simulate an expired session
# # Let's wait for more than the session duration and then check the session
# time.sleep(SESSION_DURATION + 1)  # Wait for more than SESSION_DURATION
# print("\nChecking an expired session:")
# print("Session is valid:", check_session(valid_session_id))

# # Simulate an invalid session (non-existent session ID)
# invalid_session_id = "invalid_session_id"
# print("\nChecking an invalid session:")
# print("Session is valid:", check_session(invalid_session_id))


def handle_request(environ):
    request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    request_body = environ['wsgi.input'].read(request_body_size)
    request_data = request_body.decode()

  
    cookie = SimpleCookie(environ.get('HTTP_COOKIE'))
    session_id = cookie.get('session_id')

    if session_id:
        session_id = session_id.value
        if check_session(session_id):
            
            if environ['PATH_INFO'] == '/set_trip_budget':
                return handle_set_trip_budget(request_data, session_id)
        else:
            return  handle_login()
    else:
        return  handle_login()



DB_NAME = "budgetplanner"
DB_USER = "postgres"
DB_PASSWORD = "hemanthram143"
DB_HOST = "localhost"
DB_PORT = "5432"


active_sessions = {}



def generate_token(length=16):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))




def handle_login(username, password):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            token = generate_token()
            active_sessions[token] = username
            return True, token
        else:
            return False, None
    except psycopg2.Error as e:
        print("Error connecting to PostgreSQL:", e)
        return False, None



def handle_login_request(data):
    try:
        form_data = {}
        for field in data.split("&"):
            try:
                key, value = field.split("=")
                form_data[key] = value
            except ValueError:
                print("Invalid field format:", field)

        username = form_data.get("username", "")
        password = form_data.get("password", "")
        
        success, token = handle_login(username, password)
        if success:
            
            redirect_js = f"""
            <script>
                alert("User login Successfull.");
                window.location.href = "/dashboard?token={token}";
            </script>
            """
            return redirect_js
        else:
            invalid_alert = """
            <script>
                alert("Invalid username or password. Please try again.");
                window.location.href = "/login";
            </script>
            """
            return invalid_alert
    except Exception as e:
        print("An error occurred:", e)
        return "An error occurred while processing your request."


def handle_registration_form(data):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        form_data = {}
        for field in data.split("&"):
            try:
                key, value = field.split("=")
                form_data[key] = urllib.parse.unquote_plus(value)  
            except ValueError:
                print("Invalid field format:", field)

        email = form_data.get("email", "")
        username = form_data.get("username", "")
        password = form_data.get("password", "")

        cursor.execute("INSERT INTO users (email, username, password) VALUES (%s, %s, %s)", (email, username, password))
        conn.commit()
        cursor.close()
        conn.close()
        
        
        redirect_js = """
        <script>
            alert("Registration successful! You can now login.");
            window.location.href = "/login";
        </script>
        """
        return redirect_js
    except psycopg2.Error as e:
        print("Error connecting to PostgreSQL:", e)
        return "An error occurred while processing your request."
    
def handle_add_expense_request(data, username):
    try:
        form_data = {}
        for field in data.split("&"):
            try:
                key, value = field.split("=")
                form_data[key] = value
            except ValueError:
                print("Invalid field format:", field)

        amount = float(form_data.get("amount", ""))
        category = form_data.get("category", "")
        date = form_data.get("date", "")

        
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        cursor.execute("SELECT budget_amount FROM trip_budgets WHERE username = %s", (username,))
        budget_amount = cursor.fetchone()

        if not budget_amount:
            
            cursor.close()
            conn.close()
            alert_message = "Please set a trip budget first."
            js_code = f"""
            <script>
                alert("{alert_message}");
                window.location.href = "/dashboard?username={username}";
            </script>
            """
            return js_code

        budget_amount = float(budget_amount[0])  
        if amount > budget_amount:
            cursor.close()
            conn.close()
            alert_message = "Insufficient budget amount. Cannot add expense."
            js_code = f"""
            <script>
                alert("{alert_message}");
                window.location.href = "/dashboard?username={username}";
            </script>
            """
            return js_code

     
        cursor.execute("INSERT INTO expenses (username, amount, category, date) VALUES (%s, %s, %s, %s)",
                       (username, amount, category, date))
        conn.commit()
        cursor.close()
        conn.close()

        alert_message = "Expense added successfully!"
        js_code = f"""
        <script>
            alert("{alert_message}");
            window.location.href = "/dashboard?username={username}";  // Redirect to dashboard after adding expense
        </script>
        """
        return js_code
    except psycopg2.Error as e:
        print("Error connecting to PostgreSQL:", e)
        return "An error occurred while processing your request."
    except ValueError as e:
        print("Invalid amount format:", e)
        return "Invalid amount format. Please enter a valid number."



def handle_set_trip_budget(data):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        cursor = conn.cursor()
        form_data = {}
        for field in data.split("&"):
            try:
                key, value = field.split("=")
                form_data[key] = value
            except ValueError:
                print("Invalid field format:", field)
        budget_amount = form_data.get("budget_amount", "")
        username = form_data.get("username", "")

        cursor.execute("SELECT 1 FROM trip_budgets WHERE username = %s", (username,))
        existing_budget = cursor.fetchone()

        if existing_budget:
           
            alert_message = "You already have a trip budget set."
            js_code = f"""
            <script>
                alert("{alert_message}");
                window.location.href = "/dashboard?username={username}";
            </script>
            """
            cursor.close()
            conn.close()
            return js_code
        else:
           
            cursor.execute("INSERT INTO trip_budgets (username, budget_amount) VALUES (%s, %s)", (username, budget_amount))
            conn.commit()
            cursor.close()
            conn.close()
            alert_message = "Trip budget set successfully!"
            js_code = f"""
            <script>
                alert("{alert_message}");
                window.location.href = "/dashboard?username={username}";
            </script>
            """
            return js_code
    except psycopg2.Error as e:
        print("Error connecting to PostgreSQL:", e)
        return "An error occurred while processing your request."


def handle_request(client_socket, request_data):
    try:
        print("Request data:", request_data)

        request_lines = request_data.split("\r\n")

        if not request_lines:
            print("No request lines found")
            client_socket.close()
            return

        try:
            request_method, request_route, _ = request_lines[0].split()
        except ValueError:
            print("Invalid request format")
            client_socket.close()
            return

        print("Request method:", request_method)
        print("Request route:", request_route)

        
        empty_line_index = request_data.find("\r\n\r\n")

        if empty_line_index != -1 or request_method == "GET":
            
            if request_method == "POST":
                form_data = request_data[empty_line_index + 4:]  
                if request_route == "/register":
                    response = handle_registration_form(form_data)
                elif request_route == "/login":
                    response = handle_login_request(form_data)
                elif request_route.startswith("/add_expense"):
                    username = request_route.split("=")[-1]
                    response = handle_add_expense_request(form_data, username)
                elif request_route.startswith("/set_budget"):
                    username = request_route.split("=")[-1]
                    if username:
                        response = handle_set_trip_budget(form_data)
                elif request_route == "/logout":
                    response = handle_logout(form_data)
                else:
                    response = "POST requests not supported yet."
            else:
                if request_route == "/":
                    response = """
                                <html lang="en">
                                <head>
                                    <meta charset="UTF-8">
                                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                    <title>Welcome to Trip Budget Planner</title>
                                    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
                                    <style>
                                        body {
                                            background-color: #f8f9fa;
                                        }
                                        .container {
                                            max-width: 600px;
                                            margin: 0 auto;
                                            padding-top: 100px;
                                            text-align: center;
                                        }
                                        .btn {
                                            margin-top: 20px;
                                        }
                                    </style>
                                </head>
                                <body>
                                    <div class="container">
                                        <h1 class="mt-5">Trip Budget Planner</h1>
                                        <p>Welcome to the Trip Budget Planner!</p>
                                        <p>Please <a href="/login" class="btn btn-primary">Login</a> or <a href="/register" class="btn btn-secondary">Register</a>.</p>
                                    </div>
                                </body>
                                </html>
                                """
                elif request_route == "/login":
                    response = generate_login_form()
                elif request_route == "/register":
                    response = generate_register_form()
                elif request_route.startswith("/dashboard?token"):
                    token = request_route.split("=")[-1]
                    username = active_sessions.get(token)
                    if username:
                        response = generate_dashboard_page(username)
                    else:
                        response = "Invalid token."
                elif request_route.startswith("/dashboard?username"):
                    username = request_route.split("=")[-1]
                    if username:
                        response = generate_dashboard_page(username)
                    else:
                        response = "Invalid token."
                elif request_route.startswith("/set_budget"):
                    username = request_route.split("=")[-1]
                    if username:
                        if request_method == "GET":
                            response = generate_set_budget_form(username)    
                        else:
                            response = "Invalid request method."
                    else:
                        response = "Invalid token."
                elif request_route.startswith("/expense"):
                    username = request_route.split("=")[-1]
                    response = generate_add_expense_form(username)
                
                elif request_route.startswith("/transactions"):
                    username = request_route.split("=")[-1]
                    if username:
                        response = generate_transactions_page(username)
                    else:
                        response = "Invalid token."

                    
                else:
                    response = """
                    <html>
                    <head>
                        <title>Error</title>
                        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
                    </head>
                    <body>
                        <div class="container">
                            <h1 class="mt-5">404 Not Found</h1>
                            <p>The requested page could not be found.</p>
                        </div>
                    </body>
                    </html>
                    """
        else:
            print("Invalid request format")
            client_socket.close()
            return

        print("Response:", response)
        client_socket.sendall(f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{response}".encode())
        client_socket.close()
    except Exception as e:
        print("An error occurred:", e)
        client_socket.close()

def generate_transactions_page(username):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        
        cursor.execute("SELECT budget_amount FROM trip_budgets WHERE username = %s", (username,))
        budget_row = cursor.fetchone()
        budget = budget_row[0] if budget_row else 0

        
        cursor.execute("SELECT amount, category, date FROM expenses WHERE username = %s", (username,))
        expenses = cursor.fetchall()

        
        transactions_html = f"""
        <html>
        <head>
            <title>Transactions</title>
            <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
            <style>
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                .logout-button {{
                    position: absolute;
                    top: 10px;
                    right: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="mt-5">Transactions</h1>
                <p>Budget: {budget} </p>
                <table class="table">
                    <thead class="thead-light">
                        <tr>
                            <th>Amount</th>
                            <th>Category</th>
                            <th>Date</th>
                            <th>Balance</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        

        
        balance = budget

        for expense in expenses:
            amount = expense[0]
            category = expense[1]
            date = expense[2]

            
            balance -= amount

            transactions_html += f"<tr><td>{amount}</td><td>{category}</td><td>{date}</td><td>{balance}</td></tr>"

        transactions_html += """
                        </tbody>
                    </table>
                </div>
                <button onclick="backToDashboard()" class="btn btn-primary btn-sm">Back to Dashboard</button>
                <button onclick="logout()" class="btn btn-danger logout-button btn-sm">Logout</button>
            </div>
            <script>
                function backToDashboard() {
                    window.location.href = '/dashboard?username=""" + username + """';
                }
                function logout() {
                    alert('Successfully logged out.');
                    window.location.href = '/';
                }
            </script>
        </body>
        </html>
        """

        cursor.close()
        conn.close()

        return transactions_html
    except psycopg2.Error as e:
        print("Error connecting to PostgreSQL:", e)
        return "An error occurred while processing your request."


def generate_set_budget_form(username):
    return f"""
    <html>
    <head>
        <title>Set Trip Budget</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    </head>
    <body>
        <div class="container">
            <h1 class="mt-5">Set Trip Budget</h1>
            <form action="/set_budget?username={username}" method="POST">
                <input type="hidden" name="username" value="{username}">
                <div class="form-group">
                    <label for="budget_amount"> Trip Budget Amount:</label>
                    <input type="text" class="form-control" id="budget_amount" name="budget_amount">
                </div>
                <button type="submit" class="btn btn-primary">Set Budget</button>
            </form>
        </div>
    </body>
    </html>
    """


def generate_add_expense_form(username):
    return f"""
    <html>
    <head>
        <title>Add Trip Expense</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    </head>
    <body>
        <div class="container">
            <h1 class="mt-5">Add Trip Expense</h1>
            <form action="/add_expense?username={username}" method="POST">
                <input type="hidden" name="username" value="{username}">
                <div class="form-group">
                    <label for="amount">Amount:</label>
                    <input type="text" class="form-control" id="amount" name="amount">
                </div>
                <div class="form-group">
                    <label for="category">Category:</label>
                    <input type="text" class="form-control" id="category" name="category">
                </div>
                <div class="form-group">
                    <label for="date">Date:</label>
                    <input type="date" class="form-control" id="date" name="date">
                </div>
                <button type="submit" class="btn btn-primary">Add Expense</button>
            </form>
        </div>
    </body>
    </html>
    """

def generate_login_form():
    return """
    <html>
    <html>
<head>
    <title>Login</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <style>
        body {
            background-color: #f3f5f8;
        }
        .container {
            margin-top: 100px;
        }
        .card {
            border: none;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .card-header {
            background-color: #00548f;
            color: #fff;
            border-radius: 10px 10px 0 0;
        }
        .form-control {
            border-radius: 6px;
        }
        .btn-primary {
            background-color: #00548f;
            border-color: #00548f;
        }
        .btn-primary:hover {
            background-color: #003763;
            border-color: #003763;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h3 class="text-center">Login</h3>
                    </div>
                    <div class="card-body">
                        <form action="/login" method="POST">
                            <div class="form-group">
                                <label for="username">Username:</label>
                                <input type="text" class="form-control" id="username" name="username">
                            </div>
                            <div class="form-group">
                                <label for="password">Password:</label>
                                <input type="password" class="form-control" id="password" name="password">
                            </div>
                            <button type="submit" class="btn btn-primary btn-block">Login</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>

    """


def generate_register_form():
    return """
    <html>
    <head>
        <title>Register</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
            body {
                background-color: #f3f5f8;
            }
            .container {
                margin-top: 100px;
            }
            .card {
                border: none;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .card-header {
                background-color: #00548f;
                color: #fff;
                border-radius: 10px 10px 0 0;
            }
            .form-control {
                border-radius: 6px;
            }
            .btn-primary {
                background-color: #00548f;
                border-color: #00548f;
            }
            .btn-primary:hover {
                background-color: #003763;
                border-color: #003763;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="text-center">Register</h3>
                        </div>
                        <div class="card-body">
                            <form action="/register" method="POST">
                                <div class="form-group">
                                    <label for="email">Email:</label>
                                    <input type="email" class="form-control" id="email" name="email">
                                </div>
                                <div class="form-group">
                                    <label for="username">Username:</label>
                                    <input type="text" class="form-control" id="username" name="username">
                                </div>
                                <div class="form-group">
                                    <label for="password">Password:</label>
                                    <input type="password" class="form-control" id="password" name="password">
                                </div>
                                <button type="submit" class="btn btn-primary btn-block">Register</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


def handle_logout(data):
    try:
        form_data = {}
        for field in data.split("&"):
            try:
                key, value = field.split("=")
                form_data[key] = value
            except ValueError:
                print("Invalid field format:", field)

        token = form_data.get("token", "")

        if token in active_sessions:
            del active_sessions[token]
            return generate_login_form()  
        else:
            return "Invalid token."
    except Exception as e:
        print("An error occurred:", e)
        return "An error occurred while processing your request."
    
def generate_dashboard_page(username):
    return f"""
    <html>
    <head>
    <title>Dashboard</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <style>
        body {{
            background-color: #f3f5f8;
        }}
        .container {{
            margin-top: 50px;
        }}
        .btn-primary {{
            background-color: #00548f;
            border-color: #00548f;
        }}
        .btn-primary:hover {{
            background-color: #003763;
            border-color: #003763;
        }}
        .btn-secondary {{
            background-color: #ffcd00;
            border-color: #ffcd00;
        }}
        .btn-secondary:hover {{
            background-color: #e0b600;
            border-color: #e0b600;
        }}
        .btn-info {{
            background-color: #ff8f3f;
            border-color: #ff8f3f;
        }}
        .btn-info:hover {{
            background-color: #e07731;
            border-color: #e07731;
        }}
        .logout-button {{
            position: absolute;
            top: 10px;
            right: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logout-button">
            <button onclick="logout()" class="btn btn-danger">Logout</button>
        </div>
        <h1 class="mt-5">Welcome to the TRIP Budget Planner, {username}!</h1>
        <button onclick="window.location.href='/expense?username={username}'" class="btn btn-primary">Add Expense</button>
        <button onclick="window.location.href='/set_budget?username={username}'" class="btn btn-secondary">Set Budget</button>
        <button onclick="window.location.href='/transactions?username={username}'" class="btn btn-info">View Transactions</button>
    </div>
    <script>
        function logout() {{
            alert('Successfully logged out.');
            window.location.href = '/';
        }}
    </script>
</body>
</html>
    """

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind(("localhost", 8000))
    server_socket.listen()
    print("Server is listening on http://localhost:8000")

    while True:
        client_socket, _ = server_socket.accept()
        data = client_socket.recv(1024).decode()
        print(data)
        handle_request(client_socket, data)

        client_socket.close()
