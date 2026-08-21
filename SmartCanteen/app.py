from flask import Flask, render_template, request, jsonify, session, redirect
import sqlite3
from datetime import datetime
from functools import wraps
import uuid
import json
import os
import socket
import razorpay
from dotenv import load_dotenv


# ============================================================
# SMARTCANTEEN FLASK APPLICATION
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "smartcanteen-secret-key-2026"
)

# Keep database inside the SmartCanteen project folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "smartcanteen.db")


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")


# ============================================================
# RAZORPAY CLIENT
# ============================================================

razorpay_client = None

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:

    razorpay_client = razorpay.Client(
        auth=(
            RAZORPAY_KEY_ID,
            RAZORPAY_KEY_SECRET
        )
    )

    print("Razorpay Key Loaded : True")
    print("Razorpay Client     : READY")

else:

    print("Razorpay Key Loaded : False")
    print("Razorpay Client     : NOT CONFIGURED")


# ============================================================
# LOGIN CREDENTIALS
# ============================================================

CUSTOMER_USERNAME = "student@adityauniversity"
CUSTOMER_PASSWORD = "AUS"

STAFF_USERNAME = "staff"
STAFF_PASSWORD = "staff123"

ADMIN_USERNAME = "owner"
ADMIN_PASSWORD = "owner123"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# CUSTOMER SESSION
# ============================================================

def get_customer_id():

    if session.get("customer_id"):

        return session["customer_id"]

    customer_id = str(uuid.uuid4())

    session["customer_id"] = customer_id

    return customer_id


# ============================================================
# DATABASE INITIALIZATION
# IMPORTANT:
# This function MUST run when Render starts Gunicorn.
# ============================================================

def init_db():

    conn = get_db_connection()

    # ========================================================
    # CREATE ORDERS TABLE
    # ========================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            order_id TEXT,

            customer_id TEXT,

            customer_name TEXT,

            items TEXT,

            total REAL DEFAULT 0,

            payment_method TEXT
                DEFAULT 'Cash on Pickup',

            payment_status TEXT
                DEFAULT 'Pending',

            razorpay_order_id TEXT,

            razorpay_payment_id TEXT,

            status TEXT
                DEFAULT 'Confirmed',

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        )
    """)

    conn.commit()


    # ========================================================
    # CHECK EXISTING COLUMNS
    # ========================================================

    columns = conn.execute(
        "PRAGMA table_info(orders)"
    ).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]


    # ========================================================
    # ADD MISSING COLUMNS
    # ========================================================

    if "order_id" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN order_id TEXT
        """)


    if "customer_id" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN customer_id TEXT
        """)


    if "customer_name" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN customer_name TEXT
        """)


    if "items" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN items TEXT
        """)


    if "total" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN total REAL DEFAULT 0
        """)


    if "payment_method" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN payment_method TEXT
            DEFAULT 'Cash on Pickup'
        """)


    if "payment_status" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN payment_status TEXT
            DEFAULT 'Pending'
        """)


    if "razorpay_order_id" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN razorpay_order_id TEXT
        """)


    if "razorpay_payment_id" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN razorpay_payment_id TEXT
        """)


    if "status" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN status TEXT
            DEFAULT 'Confirmed'
        """)


    if "created_at" not in column_names:

        conn.execute("""
            ALTER TABLE orders
            ADD COLUMN created_at TIMESTAMP
        """)

        conn.execute("""
            UPDATE orders
            SET created_at = CURRENT_TIMESTAMP
            WHERE created_at IS NULL
        """)


    # ========================================================
    # FIX OLD PAYMENT VALUES
    # ========================================================

    conn.execute("""
        UPDATE orders
        SET payment_method = 'Cash on Pickup'
        WHERE payment_method IS NULL
        OR payment_method = ''
    """)


    conn.execute("""
        UPDATE orders
        SET payment_status = 'Pending'
        WHERE payment_status IS NULL
        OR payment_status = ''
    """)


    # ========================================================
    # FIX OLD STATUS VALUES
    # ========================================================

    conn.execute("""
        UPDATE orders
        SET status = 'Confirmed'
        WHERE status IS NULL
        OR status = ''
    """)


    # ========================================================
    # GENERATE ORDER IDs FOR OLD ORDERS
    # ========================================================

    old_orders = conn.execute("""
        SELECT id
        FROM orders
        WHERE order_id IS NULL
        OR order_id = ''
    """).fetchall()


    for old_order in old_orders:

        generated_order_id = (
            f"SC{old_order['id']:04d}"
        )

        conn.execute("""
            UPDATE orders
            SET order_id = ?
            WHERE id = ?
        """, (
            generated_order_id,
            old_order["id"]
        ))


    conn.commit()

    conn.close()

    print("Database initialized successfully.")
    print("Database location:", DATABASE)


# ============================================================
# IMPORTANT RENDER FIX
# ============================================================
#
# Gunicorn runs:
#
#     gunicorn app:app
#
# Therefore:
#
#     if __name__ == "__main__":
#
# does NOT execute on Render.
#
# We initialize the database here so that the orders table
# exists before any API request is received.
#
# ============================================================

init_db()


# ============================================================
# STAFF LOGIN PROTECTION
# ============================================================

def staff_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if session.get("role") != "staff":

            if request.path.startswith("/api/"):

                return jsonify({

                    "success": False,

                    "message":
                        "Staff login required"

                }), 401

            return redirect("/login")

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# ADMIN LOGIN PROTECTION
# ============================================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if session.get("role") != "admin":

            if request.path.startswith("/api/"):

                return jsonify({

                    "success": False,

                    "message":
                        "Admin login required"

                }), 401

            return redirect("/login")

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    get_customer_id()

    return render_template("index.html")


# ============================================================
# MENU
# ============================================================

@app.route("/menu")
def menu():

    get_customer_id()

    return render_template("menu.html")


# ============================================================
# CART
# ============================================================

@app.route("/cart")
def cart():

    get_customer_id()

    return render_template("cart.html")


# ============================================================
# CUSTOMER ORDERS PAGE
# ============================================================

@app.route("/orders")
def orders():

    get_customer_id()

    return render_template("orders.html")


# ============================================================
# ORDER SUCCESS
# ============================================================

@app.route("/order-success")
def order_success():

    return render_template("order-success.html")


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        role = request.form.get(
            "role",
            ""
        ).strip().lower()


        # ====================================================
        # CUSTOMER
        # ====================================================

        if (
            role == "customer"
            and
            username == CUSTOMER_USERNAME
            and
            password == CUSTOMER_PASSWORD
        ):

            session.clear()

            session["role"] = "customer"

            session["username"] = username

            get_customer_id()

            return redirect("/")


        # ====================================================
        # STAFF
        # ====================================================

        elif (
            role == "staff"
            and
            username == STAFF_USERNAME
            and
            password == STAFF_PASSWORD
        ):

            session.clear()

            session["role"] = "staff"

            session["username"] = username

            return redirect("/staff")


        # ====================================================
        # ADMIN / OWNER
        # ====================================================

        elif (
            role == "owner"
            and
            username == ADMIN_USERNAME
            and
            password == ADMIN_PASSWORD
        ):

            session.clear()

            session["role"] = "admin"

            session["username"] = username

            return redirect("/admin")


        # ====================================================
        # INVALID LOGIN
        # ====================================================

        else:

            return render_template(
                "login.html",
                error="Invalid role, username or password"
            )


    return render_template("login.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ============================================================
# STAFF DASHBOARD
# ============================================================

@app.route("/staff")
@staff_required
def staff():

    return render_template("staff.html")


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
@admin_required
def admin():

    return render_template("admin.html")


# ============================================================
# RAZORPAY CREATE PAYMENT
# ============================================================

@app.route(
    "/api/payment/create",
    methods=["POST"]
)
def create_payment():

    try:

        if razorpay_client is None:

            return jsonify({

                "success": False,

                "message":
                    "Razorpay keys are not configured."

            }), 500


        data = request.get_json(
            silent=True
        ) or {}


        amount = data.get(
            "amount",
            0
        )


        try:

            amount = float(amount)

        except Exception:

            return jsonify({

                "success": False,

                "message":
                    "Invalid amount."

            }), 400


        if amount <= 0:

            return jsonify({

                "success": False,

                "message":
                    "Amount must be greater than zero."

            }), 400


        amount_paise = int(
            round(amount * 100)
        )


        razorpay_order = razorpay_client.order.create({

            "amount":
                amount_paise,

            "currency":
                "INR",

            "receipt":
                f"smartcanteen_{uuid.uuid4().hex[:12]}",

            "payment_capture":
                1

        })


        return jsonify({

            "success": True,

            "key_id":
                RAZORPAY_KEY_ID,

            "razorpay_order_id":
                razorpay_order["id"],

            "amount":
                amount_paise,

            "currency":
                "INR"

        })


    except Exception as error:

        print(
            "RAZORPAY CREATE ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                str(error)

        }), 500


# ============================================================
# RAZORPAY VERIFY PAYMENT
# ============================================================

@app.route(
    "/api/payment/verify",
    methods=["POST"]
)
def verify_payment():

    try:

        if razorpay_client is None:

            return jsonify({

                "success": False,

                "message":
                    "Razorpay is not configured."

            }), 500


        data = request.get_json(
            silent=True
        ) or {}


        razorpay_order_id = data.get(
            "razorpay_order_id"
        )

        razorpay_payment_id = data.get(
            "razorpay_payment_id"
        )

        razorpay_signature = data.get(
            "razorpay_signature"
        )


        if not all([

            razorpay_order_id,

            razorpay_payment_id,

            razorpay_signature

        ]):

            return jsonify({

                "success": False,

                "message":
                    "Incomplete payment details."

            }), 400


        verification_data = {

            "razorpay_order_id":
                razorpay_order_id,

            "razorpay_payment_id":
                razorpay_payment_id,

            "razorpay_signature":
                razorpay_signature

        }


        razorpay_client.utility.verify_payment_signature(
            verification_data
        )


        return jsonify({

            "success": True,

            "payment_status":
                "Paid",

            "razorpay_order_id":
                razorpay_order_id,

            "razorpay_payment_id":
                razorpay_payment_id,

            "message":
                "Payment verified successfully"

        })


    except Exception as error:

        print(
            "PAYMENT VERIFY ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                "Payment verification failed."

        }), 400


# ============================================================
# CREATE CUSTOMER ORDER
# ============================================================

@app.route(
    "/api/orders",
    methods=["POST"]
)
def create_order():

    try:

        customer_id = get_customer_id()


        data = request.get_json(
            silent=True
        ) or {}


        customer_name = data.get(
            "customer_name",
            "Guest"
        )


        customer_name = str(
            customer_name
        ).strip()


        if not customer_name:

            customer_name = "Guest"


        session["customer_name"] = customer_name


        items = data.get(
            "items",
            ""
        )


        if items is None:

            items = ""


        total = data.get(
            "total",
            0
        )


        try:

            total = float(total)

        except Exception:

            total = 0


        if total <= 0:

            return jsonify({

                "success": False,

                "message":
                    "Invalid order amount."

            }), 400


        payment_method = data.get(
            "payment_method",
            "Cash on Pickup"
        )


        payment_method = str(
            payment_method
        ).strip()


        allowed_payment_methods = [

            "Cash on Pickup",

            "UPI",

            "Card"

        ]


        if payment_method not in allowed_payment_methods:

            payment_method = "Cash on Pickup"


        payment_status = data.get(
            "payment_status",
            "Pending"
        )


        payment_status = str(
            payment_status
        ).strip()


        if payment_method == "Cash on Pickup":

            payment_status = "Pending"


        elif payment_method in [

            "UPI",

            "Card"

        ]:

            if payment_status != "Paid":

                return jsonify({

                    "success": False,

                    "message":
                        "Please complete payment first."

                }), 400


        razorpay_order_id = data.get(
            "razorpay_order_id"
        )

        razorpay_payment_id = data.get(
            "razorpay_payment_id"
        )


        # ====================================================
        # DATABASE CONNECTION
        # ====================================================

        conn = get_db_connection()


        # ====================================================
        # FIND NEXT ORDER NUMBER
        # ====================================================

        last_order = conn.execute("""
            SELECT id
            FROM orders
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()


        if last_order:

            next_id = (
                last_order["id"] + 1
            )

        else:

            next_id = 1


        order_id = (
            f"SC{next_id:04d}"
        )


        # ====================================================
        # INSERT ORDER
        # ====================================================

        cursor = conn.execute("""
            INSERT INTO orders
            (
                order_id,
                customer_id,
                customer_name,
                items,
                total,
                payment_method,
                payment_status,
                razorpay_order_id,
                razorpay_payment_id,
                status,
                created_at
            )

            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                CURRENT_TIMESTAMP
            )
        """, (

            order_id,

            customer_id,

            customer_name,

            items,

            total,

            payment_method,

            payment_status,

            razorpay_order_id,

            razorpay_payment_id,

            "Confirmed"

        ))


        database_id = cursor.lastrowid


        conn.commit()

        conn.close()


        return jsonify({

            "success": True,

            "order_id":
                order_id,

            "database_id":
                database_id,

            "payment_method":
                payment_method,

            "payment_status":
                payment_status,

            "message":
                "Order placed successfully"

        })


    except Exception as error:

        print(
            "ORDER ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                str(error)

        }), 500


# ============================================================
# CUSTOMER OWN ORDERS
# ============================================================

@app.route(
    "/api/customer/orders",
    methods=["GET"]
)
def customer_orders():

    try:

        customer_id = get_customer_id()


        conn = get_db_connection()


        orders = conn.execute("""
            SELECT *
            FROM orders
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (
            customer_id,
        )).fetchall()


        conn.close()


        return jsonify([

            dict(order)

            for order in orders

        ])


    except Exception as error:

        print(
            "CUSTOMER ORDERS ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                str(error)

        }), 500


# ============================================================
# ALL / CUSTOMER ORDERS
# ============================================================

@app.route(
    "/api/orders",
    methods=["GET"]
)
def get_orders():

    try:

        conn = get_db_connection()


        if session.get("role") in [

            "staff",

            "admin"

        ]:

            orders = conn.execute("""
                SELECT *
                FROM orders
                ORDER BY id DESC
            """).fetchall()


        else:

            customer_id = get_customer_id()


            orders = conn.execute("""
                SELECT *
                FROM orders
                WHERE customer_id = ?
                ORDER BY id DESC
            """, (
                customer_id,
            )).fetchall()


        conn.close()


        return jsonify([

            dict(order)

            for order in orders

        ])


    except Exception as error:

        print(
            "GET ORDERS ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                str(error)

        }), 500


# ============================================================
# STAFF ALL ORDERS
# ============================================================

@app.route(
    "/api/staff/orders",
    methods=["GET"]
)
@staff_required
def staff_orders():

    try:

        conn = get_db_connection()


        orders = conn.execute("""
            SELECT *
            FROM orders
            ORDER BY id DESC
        """).fetchall()


        conn.close()


        return jsonify([

            dict(order)

            for order in orders

        ])


    except Exception as error:

        print(
            "STAFF ORDERS ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                str(error)

        }), 500


# ============================================================
# STAFF UPDATE ORDER STATUS
# ============================================================

@app.route(
    "/api/orders/<int:order_id>/status",
    methods=["PUT"]
)
@staff_required
def update_order_status(order_id):

    try:

        data = request.get_json(
            silent=True
        ) or {}


        new_status = data.get(
            "status"
        )


        allowed_statuses = [

            "Confirmed",

            "Preparing",

            "Ready",

            "Completed"

        ]


        if new_status not in allowed_statuses:

            return jsonify({

                "success": False,

                "message":
                    "Invalid status"

            }), 400


        conn = get_db_connection()


        existing_order = conn.execute("""
            SELECT id
            FROM orders
            WHERE id = ?
        """, (
            order_id,
        )).fetchone()


        if not existing_order:

            conn.close()

            return jsonify({

                "success": False,

                "message":
                    "Order not found"

            }), 404


        conn.execute("""
            UPDATE orders
            SET status = ?
            WHERE id = ?
        """, (

            new_status,

            order_id

        ))


        conn.commit()

        conn.close()


        return jsonify({

            "success": True,

            "message":
                "Order status updated"

        })


    except Exception as error:

        print(
            "STATUS UPDATE ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                str(error)

        }), 500


# ============================================================
# ADMIN STATISTICS
# ============================================================

@app.route(
    "/api/admin/stats"
)
@admin_required
def admin_stats():

    conn = get_db_connection()


    total_orders = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
    """).fetchone()["count"]


    total_revenue = conn.execute("""
        SELECT
            COALESCE(
                SUM(total),
                0
            ) AS revenue
        FROM orders
        WHERE payment_status = 'Paid'
        OR payment_method = 'Cash on Pickup'
    """).fetchone()["revenue"]


    pending_orders = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
        WHERE status IN
        (
            'Confirmed',
            'Preparing',
            'Ready'
        )
    """).fetchone()["count"]


    completed_orders = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
        WHERE status = 'Completed'
    """).fetchone()["count"]


    confirmed_orders = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
        WHERE status = 'Confirmed'
    """).fetchone()["count"]


    preparing_orders = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
        WHERE status = 'Preparing'
    """).fetchone()["count"]


    ready_orders = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
        WHERE status = 'Ready'
    """).fetchone()["count"]


    conn.close()


    return jsonify({

        "total_orders":
            total_orders,

        "total_revenue":
            total_revenue,

        "pending_orders":
            pending_orders,

        "completed_orders":
            completed_orders,

        "confirmed_orders":
            confirmed_orders,

        "preparing_orders":
            preparing_orders,

        "ready_orders":
            ready_orders

    })


# ============================================================
# ADMIN RECENT ORDERS
# ============================================================

@app.route(
    "/api/admin/orders"
)
@admin_required
def admin_orders():

    conn = get_db_connection()


    orders = conn.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()


    conn.close()


    return jsonify([

        dict(order)

        for order in orders

    ])


# ============================================================
# ADMIN ANALYTICS
# ============================================================

@app.route(
    "/api/admin/analytics"
)
@admin_required
def admin_analytics():

    conn = get_db_connection()


    today = datetime.now().strftime(
        "%Y-%m-%d"
    )


    today_orders = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
        WHERE DATE(created_at) = ?
    """, (
        today,
    )).fetchone()["count"]


    today_revenue = conn.execute("""
        SELECT
            COALESCE(
                SUM(total),
                0
            ) AS revenue
        FROM orders
        WHERE DATE(created_at) = ?
        AND
        (
            payment_status = 'Paid'
            OR payment_method = 'Cash on Pickup'
        )
    """, (
        today,
    )).fetchone()["revenue"]


    average_order = conn.execute("""
        SELECT
            COALESCE(
                AVG(total),
                0
            ) AS average
        FROM orders
    """).fetchone()["average"]


    today_completed = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
        WHERE DATE(created_at) = ?
        AND status = 'Completed'
    """, (
        today,
    )).fetchone()["count"]


    today_pending = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
        WHERE DATE(created_at) = ?
        AND status IN
        (
            'Confirmed',
            'Preparing',
            'Ready'
        )
    """, (
        today,
    )).fetchone()["count"]


    conn.close()


    return jsonify({

        "today_orders":
            today_orders,

        "today_revenue":
            today_revenue,

        "average_order":
            average_order,

        "today_completed":
            today_completed,

        "today_pending":
            today_pending

    })


# ============================================================
# ADMIN DAILY REVENUE
# ============================================================

@app.route(
    "/api/admin/daily-revenue"
)
@admin_required
def daily_revenue():

    conn = get_db_connection()


    revenue = conn.execute("""
        SELECT

            DATE(created_at)
            AS date,

            COUNT(*)
            AS orders,

            COALESCE(
                SUM(total),
                0
            )
            AS revenue

        FROM orders

        WHERE
            payment_status = 'Paid'
            OR payment_method = 'Cash on Pickup'

        GROUP BY
            DATE(created_at)

        ORDER BY
            date ASC
    """).fetchall()


    conn.close()


    return jsonify([

        dict(row)

        for row in revenue

    ])


# ============================================================
# ADMIN POPULAR ITEMS
# ============================================================

@app.route(
    "/api/admin/popular-items"
)
@admin_required
def popular_items():

    try:

        conn = get_db_connection()


        orders = conn.execute("""
            SELECT items
            FROM orders
            ORDER BY id DESC
        """).fetchall()


        conn.close()


        item_summary = {}


        for order in orders:

            raw_items = order["items"]


            if not raw_items:

                continue


            # =================================================
            # JSON FORMAT
            # =================================================

            try:

                if isinstance(
                    raw_items,
                    str
                ):

                    parsed_items = json.loads(
                        raw_items
                    )

                else:

                    parsed_items = raw_items


                if isinstance(
                    parsed_items,
                    dict
                ):

                    parsed_items = [
                        parsed_items
                    ]


                if isinstance(
                    parsed_items,
                    list
                ):

                    for item in parsed_items:

                        if not isinstance(
                            item,
                            dict
                        ):

                            continue


                        name = str(
                            item.get(
                                "name",
                                "Unknown Food"
                            )
                        ).strip()


                        if not name:

                            name = "Unknown Food"


                        try:

                            quantity = int(
                                item.get(
                                    "quantity",
                                    1
                                )
                            )

                        except Exception:

                            quantity = 1


                        if quantity < 1:

                            quantity = 1


                        if name not in item_summary:

                            item_summary[name] = 0


                        item_summary[name] += quantity


                    continue


            except Exception:

                pass


            # =================================================
            # TEXT FALLBACK
            # =================================================

            text_items = str(
                raw_items
            ).strip()


            if text_items:

                parts = text_items.split(",")


                for part in parts:

                    item_name = part.strip()


                    if not item_name:

                        continue


                    if item_name not in item_summary:

                        item_summary[item_name] = 0


                    item_summary[item_name] += 1


        popular = [

            {
                "name": name,
                "quantity": quantity
            }

            for name, quantity
            in item_summary.items()

        ]


        popular.sort(
            key=lambda x: x["quantity"],
            reverse=True
        )


        return jsonify(
            popular[:10]
        )


    except Exception as error:

        print(
            "POPULAR ITEMS ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                str(error)

        }), 500


# ============================================================
# ADMIN PAYMENT SUMMARY
# ============================================================

@app.route(
    "/api/admin/payment-summary"
)
@admin_required
def payment_summary():

    try:

        conn = get_db_connection()


        # ====================================================
        # CASH
        # ====================================================

        cash_data = conn.execute("""
            SELECT
                COUNT(*) AS count,
                COALESCE(
                    SUM(total),
                    0
                ) AS amount
            FROM orders
            WHERE payment_method =
                'Cash on Pickup'
        """).fetchone()


        # ====================================================
        # UPI
        # ====================================================

        upi_data = conn.execute("""
            SELECT
                COUNT(*) AS count,
                COALESCE(
                    SUM(total),
                    0
                ) AS amount
            FROM orders
            WHERE payment_method = 'UPI'
            AND payment_status = 'Paid'
        """).fetchone()


        # ====================================================
        # CARD
        # ====================================================

        card_data = conn.execute("""
            SELECT
                COUNT(*) AS count,
                COALESCE(
                    SUM(total),
                    0
                ) AS amount
            FROM orders
            WHERE payment_method = 'Card'
            AND payment_status = 'Paid'
        """).fetchone()


        total_payment_orders = (

            cash_data["count"]

            +

            upi_data["count"]

            +

            card_data["count"]

        )


        # ====================================================
        # PERCENTAGES
        # ====================================================

        if total_payment_orders > 0:

            cash_percentage = (

                cash_data["count"]

                /

                total_payment_orders

            ) * 100


            upi_percentage = (

                upi_data["count"]

                /

                total_payment_orders

            ) * 100


            card_percentage = (

                card_data["count"]

                /

                total_payment_orders

            ) * 100

        else:

            cash_percentage = 0

            upi_percentage = 0

            card_percentage = 0


        conn.close()


        return jsonify({

            "cash": {

                "count":
                    cash_data["count"],

                "amount":
                    cash_data["amount"],

                "percentage":
                    round(
                        cash_percentage,
                        2
                    )

            },

            "upi": {

                "count":
                    upi_data["count"],

                "amount":
                    upi_data["amount"],

                "percentage":
                    round(
                        upi_percentage,
                        2
                    )

            },

            "card": {

                "count":
                    card_data["count"],

                "amount":
                    card_data["amount"],

                "percentage":
                    round(
                        card_percentage,
                        2
                    )

            },

            "total": {

                "count":
                    total_payment_orders,

                "amount":
                    (
                        cash_data["amount"]
                        +
                        upi_data["amount"]
                        +
                        card_data["amount"]
                    )

            }

        })


    except Exception as error:

        print(
            "PAYMENT SUMMARY ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                str(error)

        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health")
def health():

    return jsonify({

        "success": True,

        "message":
            "SmartCanteen server is running"

    })


# ============================================================
# FIND LOCAL IP ADDRESS
# ============================================================

def get_local_ip():

    try:

        hostname = socket.gethostname()

        local_ip = socket.gethostbyname(
            hostname
        )

        if local_ip.startswith("127."):

            sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM
            )

            try:

                sock.connect(
                    ("8.8.8.8", 80)
                )

                local_ip = sock.getsockname()[0]

            finally:

                sock.close()


        return local_ip


    except Exception:

        return "YOUR-PC-IP"


# ============================================================
# SERVER START
# ============================================================

if __name__ == "__main__":

    # Database is already initialized above.
    # This is kept here as an extra safety check for local use.

    init_db()


    local_ip = get_local_ip()


    print("")
    print("==================================================")
    print("             SMARTCANTEEN SERVER")
    print("==================================================")

    print("")
    print("Server Status : RUNNING")
    print("")

    print(
        "Computer URL  : "
        "http://127.0.0.1:5000/"
    )

    print(
        "Network URL   : "
        f"http://{local_ip}:5000/"
    )

    print("")

    print(
        "Login URL     : "
        f"http://{local_ip}:5000/login"
    )

    print(
        "Staff URL     : "
        f"http://{local_ip}:5000/staff"
    )

    print(
        "Admin URL     : "
        f"http://{local_ip}:5000/admin"
    )

    print("")

    print("==================================================")
    print("PHONE ACCESS")
    print("==================================================")

    print(
        "Open this link on your phone:"
    )

    print(
        f"http://{local_ip}:5000/"
    )

    print("")

    print("IMPORTANT:")

    print(
        "1. PC and phone must be connected"
    )

    print(
        "   to the same Wi-Fi network."
    )

    print(
        "2. Keep this terminal window open."
    )

    print(
        "3. If Windows Firewall asks for permission,"
    )

    print(
        "   allow Python on Private Networks."
    )

    print("==================================================")
    print("")


    # ========================================================
    # START FLASK SERVER
    # ========================================================

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )