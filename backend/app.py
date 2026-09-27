from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()

# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)
CORS(app)


# ============================================================
# PATH TO FRONTEND
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")


# ============================================================
# DATABASE CONNECTION
# ============================================================
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "BankDB"),
        port=int(os.getenv("DB_PORT", "3306"))
    )

# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():
    return redirect("/login.html")


# ============================================================
# SERVE FRONTEND FILES
# ============================================================

@app.route("/<path:filename>")
def serve_frontend(filename):

    return send_from_directory(
        FRONTEND_DIR,
        filename
    )


# ============================================================
# CUSTOMER LOGIN
# ============================================================

@app.route("/login", methods=["POST"])
def login():

    try:

        data = request.get_json()

        account = str(data.get("account", "")).strip()
        pin = str(data.get("pin", "")).strip()

        if not account or not pin:

            return jsonify({
                "status": "error",
                "message": "Please enter Account Number and PIN."
            })

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                Customer.Name,
                Account.Balance
            FROM Customer
            JOIN Account
                ON Customer.Customer_ID = Account.Customer_ID
            JOIN Customer_Login
                ON Account.Account_No = Customer_Login.Account_No
            WHERE Account.Account_No = %s
            AND Customer_Login.Password = %s
        """

        cursor.execute(
            query,
            (account, pin)
        )

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:

            return jsonify({
                "status": "success",
                "name": result["Name"],
                "balance": float(result["Balance"])
            })

        return jsonify({
            "status": "error",
            "message": "Invalid Account Number or PIN."
        })

    except Exception as e:

        print("LOGIN ERROR:", e)

        return jsonify({
            "status": "error",
            "message": "Database connection error."
        })


# ============================================================
# GET BALANCE
# ============================================================

@app.route("/balance", methods=["GET"])
def get_balance():

    try:

        account = request.args.get("account")

        if not account:

            return jsonify({
                "status": "error",
                "message": "Account number is required."
            })

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT Balance
            FROM Account
            WHERE Account_No = %s
            """,
            (account,)
        )

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:

            return jsonify({
                "status": "success",
                "balance": float(result["Balance"])
            })

        return jsonify({
            "status": "error",
            "message": "Account not found."
        })

    except Exception as e:

        print("BALANCE ERROR:", e)

        return jsonify({
            "status": "error",
            "message": "Unable to retrieve balance."
        })


# ============================================================
# DEPOSIT
# ============================================================

@app.route("/deposit", methods=["POST"])
def deposit():

    conn = None

    try:

        data = request.get_json()

        account = str(data.get("account", "")).strip()
        amount = float(data.get("amount", 0))

        if not account:

            return jsonify({
                "status": "error",
                "message": "Account number is required."
            })

        if amount <= 0:

            return jsonify({
                "status": "error",
                "message": "Enter a valid amount."
            })

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check account
        cursor.execute(
            """
            SELECT Balance
            FROM Account
            WHERE Account_No = %s
            """,
            (account,)
        )

        account_data = cursor.fetchone()

        if not account_data:

            cursor.close()
            conn.close()

            return jsonify({
                "status": "error",
                "message": "Account not found."
            })

        # Update balance
        cursor.execute(
            """
            UPDATE Account
            SET Balance = Balance + %s
            WHERE Account_No = %s
            """,
            (amount, account)
        )

        # Add transaction
        cursor.execute(
            """
            INSERT INTO Transaction_Details
            (
                Account_No,
                Transaction_Type,
                Amount,
                Transaction_Date
            )
            VALUES
            (
                %s,
                'Deposit',
                %s,
                NOW()
            )
            """,
            (account, amount)
        )

        # Get new balance
        cursor.execute(
            """
            SELECT Balance
            FROM Account
            WHERE Account_No = %s
            """,
            (account,)
        )

        new_balance = cursor.fetchone()["Balance"]

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "balance": float(new_balance)
        })

    except Exception as e:

        if conn:
            conn.rollback()
            conn.close()

        print("DEPOSIT ERROR:", e)

        return jsonify({
            "status": "error",
            "message": "Deposit failed."
        })


# ============================================================
# WITHDRAW
# ============================================================

@app.route("/withdraw", methods=["POST"])
def withdraw():

    conn = None

    try:

        data = request.get_json()

        account = str(data.get("account", "")).strip()
        amount = float(data.get("amount", 0))

        if not account:

            return jsonify({
                "status": "error",
                "message": "Account number is required."
            })

        if amount <= 0:

            return jsonify({
                "status": "error",
                "message": "Enter a valid amount."
            })

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get current balance
        cursor.execute(
            """
            SELECT Balance
            FROM Account
            WHERE Account_No = %s
            """,
            (account,)
        )

        account_data = cursor.fetchone()

        if not account_data:

            cursor.close()
            conn.close()

            return jsonify({
                "status": "error",
                "message": "Account not found."
            })

        current_balance = float(account_data["Balance"])

        if amount > current_balance:

            cursor.close()
            conn.close()

            return jsonify({
                "status": "error",
                "message": "Insufficient balance."
            })

        # Update balance
        cursor.execute(
            """
            UPDATE Account
            SET Balance = Balance - %s
            WHERE Account_No = %s
            """,
            (amount, account)
        )

        # Add transaction
        cursor.execute(
            """
            INSERT INTO Transaction_Details
            (
                Account_No,
                Transaction_Type,
                Amount,
                Transaction_Date
            )
            VALUES
            (
                %s,
                'Withdrawal',
                %s,
                NOW()
            )
            """,
            (account, amount)
        )

        # Get new balance
        cursor.execute(
            """
            SELECT Balance
            FROM Account
            WHERE Account_No = %s
            """,
            (account,)
        )

        new_balance = cursor.fetchone()["Balance"]

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "balance": float(new_balance)
        })

    except Exception as e:

        if conn:
            conn.rollback()
            conn.close()

        print("WITHDRAW ERROR:", e)

        return jsonify({
            "status": "error",
            "message": "Withdrawal failed."
        })


# ============================================================
# TRANSFER
# ============================================================

@app.route("/transfer", methods=["POST"])
def transfer():

    conn = None

    try:

        data = request.get_json()

        sender = str(data.get("sender", "")).strip()
        receiver = str(data.get("receiver", "")).strip()
        amount = float(data.get("amount", 0))

        if not sender or not receiver:

            return jsonify({
                "status": "error",
                "message": "Sender and receiver accounts are required."
            })

        if sender == receiver:

            return jsonify({
                "status": "error",
                "message": "You cannot transfer money to the same account."
            })

        if amount <= 0:

            return jsonify({
                "status": "error",
                "message": "Enter a valid amount."
            })

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check sender
        cursor.execute(
            """
            SELECT Balance
            FROM Account
            WHERE Account_No = %s
            """,
            (sender,)
        )

        sender_data = cursor.fetchone()

        if not sender_data:

            cursor.close()
            conn.close()

            return jsonify({
                "status": "error",
                "message": "Sender account not found."
            })

        sender_balance = float(sender_data["Balance"])

        if amount > sender_balance:

            cursor.close()
            conn.close()

            return jsonify({
                "status": "error",
                "message": "Insufficient balance."
            })

        # Check receiver
        cursor.execute(
            """
            SELECT Account_No
            FROM Account
            WHERE Account_No = %s
            """,
            (receiver,)
        )

        receiver_data = cursor.fetchone()

        if not receiver_data:

            cursor.close()
            conn.close()

            return jsonify({
                "status": "error",
                "message": "Receiver account not found."
            })

        # Deduct from sender
        cursor.execute(
            """
            UPDATE Account
            SET Balance = Balance - %s
            WHERE Account_No = %s
            """,
            (amount, sender)
        )

        # Add to receiver
        cursor.execute(
            """
            UPDATE Account
            SET Balance = Balance + %s
            WHERE Account_No = %s
            """,
            (amount, receiver)
        )

        # Sender transaction
        cursor.execute(
            """
            INSERT INTO Transaction_Details
            (
                Account_No,
                Transaction_Type,
                Amount,
                Transaction_Date
            )
            VALUES
            (
                %s,
                'Transfer',
                %s,
                NOW()
            )
            """,
            (sender, amount)
        )

        # Receiver transaction
        cursor.execute(
            """
            INSERT INTO Transaction_Details
            (
                Account_No,
                Transaction_Type,
                Amount,
                Transaction_Date
            )
            VALUES
            (
                %s,
                'Transfer Received',
                %s,
                NOW()
            )
            """,
            (receiver, amount)
        )

        # Get sender's new balance
        cursor.execute(
            """
            SELECT Balance
            FROM Account
            WHERE Account_No = %s
            """,
            (sender,)
        )

        new_balance = cursor.fetchone()["Balance"]

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "balance": float(new_balance)
        })

    except Exception as e:

        if conn:
            conn.rollback()
            conn.close()

        print("TRANSFER ERROR:", e)

        return jsonify({
            "status": "error",
            "message": "Transfer failed."
        })


# ============================================================
# CUSTOMER PROFILE
# ============================================================

@app.route("/profile", methods=["GET"])
def profile():

    try:

        account = request.args.get("account")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                Customer.Name,
                Customer.Gender,
                Customer.DOB,
                Customer.Phone,
                Customer.Email,
                Customer.Address,
                Account.Account_No,
                Account.Account_Type,
                Account.Balance,
                Account.Open_Date,
                Branch.Branch_Name,
                Branch.City,
                Branch.IFSC_Code
            FROM Customer
            JOIN Account
                ON Customer.Customer_ID = Account.Customer_ID
            JOIN Branch
                ON Account.Branch_ID = Branch.Branch_ID
            WHERE Account.Account_No = %s
        """

        cursor.execute(
            query,
            (account,)
        )

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:

            result["Balance"] = float(result["Balance"])

            return jsonify({
                "status": "success",
                "profile": result
            })

        return jsonify({
            "status": "error",
            "message": "Profile not found."
        })

    except Exception as e:

        print("PROFILE ERROR:", e)

        return jsonify({
            "status": "error",
            "message": "Unable to load profile."
        })


# ============================================================
# TRANSACTION HISTORY
# ============================================================

@app.route("/transactions", methods=["GET"])
def transactions():

    try:

        account = request.args.get("account")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                Transaction_ID,
                Account_No,
                Transaction_Type,
                Amount,
                Transaction_Date
            FROM Transaction_Details
            WHERE Account_No = %s
            ORDER BY Transaction_Date DESC, Transaction_ID DESC
            """,
            (account,)
        )

        records = cursor.fetchall()

        cursor.close()
        conn.close()

        for record in records:
            record["Amount"] = float(record["Amount"])
            record["Transaction_Date"] = str(
                record["Transaction_Date"]
            )

        return jsonify({
            "status": "success",
            "transactions": records
        })

    except Exception as e:

        print("TRANSACTION ERROR:", e)

        return jsonify({
            "status": "error",
            "message": "Unable to load transactions."
        })


# ============================================================
# INVOICES
# ============================================================

@app.route("/invoices", methods=["GET"])
def invoices():

    try:

        account = request.args.get("account")

        if not account:

            return jsonify({
                "success": False,
                "message": "Account number is required."
            })

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Current balance
        cursor.execute(
            """
            SELECT
                Account.Balance,
                Customer.Name
            FROM Account
            JOIN Customer
                ON Account.Customer_ID = Customer.Customer_ID
            WHERE Account.Account_No = %s
            """,
            (account,)
        )

        account_data = cursor.fetchone()

        if not account_data:

            cursor.close()
            conn.close()

            return jsonify({
                "success": False,
                "message": "Account not found."
            })

        current_balance = float(account_data["Balance"])
        customer_name = account_data["Name"]

        # Transactions
        cursor.execute(
            """
            SELECT
                Transaction_ID,
                Account_No,
                Transaction_Type,
                Amount,
                Transaction_Date
            FROM Transaction_Details
            WHERE Account_No = %s
            ORDER BY Transaction_ID DESC
            """,
            (account,)
        )

        transactions = cursor.fetchall()

        cursor.close()
        conn.close()

        invoices = []

        # Reconstruct previous balances from current balance
        running_balance = current_balance

        for transaction in transactions:

            amount = float(transaction["Amount"])
            transaction_type = transaction["Transaction_Type"]

            new_balance = running_balance

            if transaction_type in [
                "Deposit",
                "Transfer Received"
            ]:

                old_balance = running_balance - amount

            elif transaction_type in [
                "Withdrawal",
                "Transfer"
            ]:

                old_balance = running_balance + amount

            else:

                old_balance = running_balance

            invoice = {
                "transaction_id":
                    transaction["Transaction_ID"],

                "account":
                    transaction["Account_No"],

                "name":
                    customer_name,

                "type":
                    transaction_type,

                "amount":
                    amount,

                "old_balance":
                    round(old_balance, 2),

                "balance":
                    round(new_balance, 2),

                "date":
                    str(transaction["Transaction_Date"])
            }

            invoices.append(invoice)

            running_balance = old_balance

        return jsonify({
            "success": True,
            "invoices": invoices
        })

    except Exception as e:

        print("INVOICE ERROR:", e)

        return jsonify({
            "success": False,
            "message": "Unable to load invoices."
        })

# =========================
# EMPLOYEE LOGIN
# =========================
@app.route("/employee-login", methods=["POST"])
def employee_login():
    data = request.get_json()

    employee_id = data.get("employee_id")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            e.Employee_ID,
            e.Employee_Name,
            e.Employee_Position,
            b.Branch_Name
        FROM Employee e
        JOIN Employee_Login el
            ON e.Employee_ID = el.Employee_ID
        JOIN Branch b
            ON e.Branch_ID = b.Branch_ID
        WHERE e.Employee_ID = %s
        AND el.Password = %s
    """

    cursor.execute(query, (employee_id, password))
    employee = cursor.fetchone()

    cursor.close()
    conn.close()

    if employee:
        return jsonify({
            "status": "success",
            "employee_id": employee["Employee_ID"],
            "name": employee["Employee_Name"],
            "position": employee["Employee_Position"],
            "branch": employee["Branch_Name"]
        })

    return jsonify({
        "status": "error",
        "message": "Invalid Employee ID or Password"
    }), 401

# =========================
# EMPLOYEE - VIEW CUSTOMERS
# =========================
@app.route("/employee/customers", methods=["GET"])
def employee_customers():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            Customer_ID,
            Name,
            Gender,
            DOB,
            Phone,
            Email,
            Address
        FROM Customer
        ORDER BY Customer_ID
    """

    cursor.execute(query)
    customers = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(customers)



# =========================
# EMPLOYEE - VIEW ACCOUNTS
# =========================
@app.route("/employee/accounts", methods=["GET"])
def employee_accounts():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            a.Account_No,
            a.Customer_ID,
            c.Name AS Customer_Name,
            a.Branch_ID,
            b.Branch_Name,
            a.Account_Type,
            a.Balance,
            a.Open_Date
        FROM Account a
        JOIN Customer c
            ON a.Customer_ID = c.Customer_ID
        JOIN Branch b
            ON a.Branch_ID = b.Branch_ID
        ORDER BY a.Account_No
    """

    cursor.execute(query)
    accounts = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(accounts)

# =========================
# EMPLOYEE - VIEW BRANCHES
# =========================
@app.route("/employee/branches", methods=["GET"])
def employee_branches():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            Branch_ID,
            Branch_Name,
            City,
            IFSC_Code
        FROM Branch
        ORDER BY Branch_ID
    """

    cursor.execute(query)
    branches = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(branches)



# =========================
# EMPLOYEE - VIEW LOANS
# =========================
@app.route("/employee/loans", methods=["GET"])
def employee_loans():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            l.Loan_ID,
            l.Customer_ID,
            c.Name AS Customer_Name,
            l.Loan_Type,
            l.Loan_Amount,
            l.Interest_Rate
        FROM Loan l
        JOIN Customer c
            ON l.Customer_ID = c.Customer_ID
        ORDER BY l.Loan_ID
    """

    cursor.execute(query)
    loans = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(loans)
# =========================
# EMPLOYEE - VIEW TRANSACTIONS
# =========================
@app.route("/employee/transactions", methods=["GET"])
def employee_transactions():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            t.Transaction_ID,
            t.Account_No,
            c.Name AS Customer_Name,
            t.Transaction_Type,
            t.Amount,
            t.Transaction_Date
        FROM Transaction_Details t
        JOIN Account a
            ON t.Account_No = a.Account_No
        JOIN Customer c
            ON a.Customer_ID = c.Customer_ID
        ORDER BY t.Transaction_Date DESC, t.Transaction_ID DESC
    """

    cursor.execute(query)
    transactions = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(transactions)

@app.route("/employee/search", methods=["GET"])
def employee_search():

    search_type = request.args.get("type", "")
    query_value = request.args.get("query", "").strip()

    if not query_value:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # SEARCH BY CUSTOMER ID

        if search_type == "customer_id":

            query = """
                SELECT
                    c.Customer_ID,
                    c.Name,
                    c.Gender,
                    c.Phone,
                    c.Email,
                    a.Account_No,
                    a.Account_Type,
                    a.Balance
                FROM Customer c
                LEFT JOIN Account a
                    ON c.Customer_ID = a.Customer_ID
                WHERE c.Customer_ID = %s
            """

            cursor.execute(query, (query_value,))


        # SEARCH BY CUSTOMER NAME

        elif search_type == "customer_name":

            query = """
                SELECT
                    c.Customer_ID,
                    c.Name,
                    c.Gender,
                    c.Phone,
                    c.Email,
                    a.Account_No,
                    a.Account_Type,
                    a.Balance
                FROM Customer c
                LEFT JOIN Account a
                    ON c.Customer_ID = a.Customer_ID
                WHERE c.Name LIKE %s
            """

            cursor.execute(
                query,
                ("%" + query_value + "%",)
            )


        # SEARCH BY ACCOUNT NUMBER

        elif search_type == "account_no":

            query = """
                SELECT
                    a.Account_No,
                    c.Customer_ID,
                    c.Name AS Customer_Name,
                    b.Branch_Name,
                    a.Account_Type,
                    a.Balance,
                    a.Open_Date
                FROM Account a
                JOIN Customer c
                    ON a.Customer_ID = c.Customer_ID
                JOIN Branch b
                    ON a.Branch_ID = b.Branch_ID
                WHERE a.Account_No = %s
            """

            cursor.execute(query, (query_value,))


        else:

            return jsonify({
                "status": "error",
                "message": "Invalid search type"
            }), 400


        results = cursor.fetchall()

        return jsonify(results)


    except Exception as e:

        print("Search Error:", e)

        return jsonify({
            "status": "error",
            "message": "Unable to search records"
        }), 500


    finally:

        cursor.close()
        conn.close()
# ============================================================
# RUN SERVER
# ============================================================
if __name__ == "__main__":
    print("Smart Digital Bank Server Started")
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )