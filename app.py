import streamlit as st
import sqlite3
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import uuid
from twilio.rest import Client
import schedule
import time
import threading

# Add these to your Streamlit secrets or use environment variables
TWILIO_ACCOUNT_SID = ""
TWILIO_AUTH_TOKEN = ""
TWILIO_PHONE_NUMBER = ""

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# SMS Functions
def send_sms(to_number, message):
    try:
        message = twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )
        return True
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")
        return False

def get_monthly_investment_summary(user_id):
    conn = sqlite3.connect('investments.db')
    try:
        # Get user details
        user_df = pd.read_sql_query("SELECT * FROM users WHERE user_id = ?",
                                   conn, params=(user_id,))

        # Get investment details
        investments_df = pd.read_sql_query("""
            SELECT * FROM investments
            WHERE user_id = ?
        """, conn, params=(user_id,))

        if not investments_df.empty:
            total_amount = 0
            total_interest = 0

            for _, inv in investments_df.iterrows():
                interest = calculate_interest(inv['amount'], inv['interest_rate'], 1)  # Calculate for one month
                total_amount += inv['amount']
                total_interest += interest

            message = (f"Monthly Investment Update\n"
                      f"Total Investment: ₹{total_amount:,.2f}\n"
                      f"This Month's Interest: ₹{total_interest:,.2f}\n"
                      f"Total Amount: ₹{(total_amount + total_interest):,.2f}")

            return user_df.iloc[0]['mobile'], message
    finally:
        conn.close()

def send_monthly_updates():
    conn = sqlite3.connect('investments.db')
    users_df = pd.read_sql_query("SELECT DISTINCT user_id FROM investments", conn)
    conn.close()

    for _, user in users_df.iterrows():
        phone, message = get_monthly_investment_summary(user['user_id'])
        if phone and message:
            send_sms(phone, message)

# Schedule monthly updates
def run_scheduler():
    schedule.every().month.at("10:00").do(send_monthly_updates)
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Check every hour

# Start scheduler in a separate thread
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

# Database Functions
def init_db():
    conn = sqlite3.connect('investments.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id TEXT PRIMARY KEY,
                  name TEXT,
                  mobile TEXT,
                  email TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS investments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  amount REAL,
                  interest_rate REAL,
                  months INTEGER,
                  date TEXT,
                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect('investments.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM investments WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        conn.close()

def update_user(user_id, name, mobile, email):
    conn = sqlite3.connect('investments.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET name=?, mobile=?, email=? WHERE user_id=?",
                 (name, mobile, email, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        conn.close()

def calculate_interest(principal, rate, months):
    """Calculate interest amount based on fixed rate per month"""
    monthly_rate = rate / 100
    total_interest = principal * monthly_rate * months
    return total_interest

# Initialize the database
init_db()

# Page configuration
st.set_page_config(page_title="Investment Tracker", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar navigation
page = st.sidebar.selectbox("Navigate to", ["User Registration", "Investment Management", "Reports"])

if page == "User Registration":
    st.title("User Registration")

    with st.form("registration_form"):
        name = st.text_input("Name")
        mobile = st.text_input("Mobile")
        email = st.text_input("Email (Optional)")

        submit_button = st.form_submit_button("Register User")

        if submit_button:
            if name and mobile:
                try:
                    user_id = str(uuid.uuid4())
                    conn = sqlite3.connect('investments.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                            (user_id, name, mobile, email))
                    conn.commit()
                    conn.close()

                    # Send welcome SMS
                    welcome_message = f"Welcome to Investment Tracker, {name}! You have been successfully registered."
                    if send_sms(mobile, welcome_message):
                        st.success("User registered successfully and welcome SMS sent!")
                    else:
                        st.success("User registered successfully but SMS failed to send.")
                except Exception as e:
                    st.error(f"Error registering user: {str(e)}")
            else:
                st.warning("Please fill required fields (Name and Mobile)!")

    # Display users table
    st.subheader("Registered Users")
    conn = sqlite3.connect('investments.db')
    users_df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()

    if not users_df.empty:
        for index, user in users_df.iterrows():
            with st.expander(f"{user['name']} - {user['mobile']}"):
                with st.form(f"edit_user_{user['user_id']}"):
                    edit_name = st.text_input("Name", value=user['name'])
                    edit_mobile = st.text_input("Mobile", value=user['mobile'])
                    edit_email = st.text_input("Email", value=user['email'] if user['email'] else "")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update"):
                            if update_user(user['user_id'], edit_name, edit_mobile, edit_email):
                                st.success("User updated successfully!")
                                st.experimental_rerun()
                            else:
                                st.error("Error updating user!")
                    with col2:
                        if st.form_submit_button("Delete"):
                            if delete_user(user['user_id']):
                                st.success("User deleted successfully!")
                                st.experimental_rerun()
                            else:
                                st.error("Error deleting user!")
    else:
        st.info("No users registered yet.")

elif page == "Investment Management":
    st.title("Investment Management")

    conn = sqlite3.connect('investments.db')
    users_df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()

    if users_df.empty:
        st.warning("Please register users first before adding investments.")
    else:
        with st.form("investment_form", clear_on_submit=True):
            user_dict = {f"{row['name']} ({row['mobile']})": row['user_id']
                        for _, row in users_df.iterrows()}

            selected_user_display = st.selectbox("Select User", list(user_dict.keys()))
            selected_user_id = user_dict[selected_user_display]

            amount = st.number_input("Investment Amount", min_value=0.0)
            interest_rate = st.number_input("Interest Rate (% per month)",
                                          min_value=0.0, max_value=100.0, value=5.0)
            months = st.number_input("Number of Months", min_value=1, value=12)
            date = st.date_input("Investment Date")

            send_sms_notification = st.checkbox("Send SMS confirmation to user")

            if amount > 0:
                interest = calculate_interest(amount, interest_rate, months)
                total = amount + interest
                st.write(f"Preview: Principal: ₹{amount:,.2f}")
                st.write(f"Monthly Interest Rate: {interest_rate}%")
                st.write(f"Total Interest: ₹{interest:,.2f}")
                st.write(f"Final Amount: ₹{total:,.2f}")

            submitted = st.form_submit_button("Add Investment")

            if submitted:
                if amount > 0:
                    conn = sqlite3.connect('investments.db')
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO investments
                        (user_id, amount, interest_rate, months, date)
                        VALUES (?, ?, ?, ?, ?)
                    """, (selected_user_id, amount, interest_rate, months,
                         date.strftime('%Y-%m-%d')))
                    conn.commit()

                    if send_sms_notification:
                        user_data = pd.read_sql_query(
                            "SELECT mobile FROM users WHERE user_id = ?",
                            conn, params=(selected_user_id,))
                        if not user_data.empty:
                            phone = user_data.iloc[0]['mobile']
                            message = (
                                f"New Investment Registered\n"
                                f"Amount: ₹{amount:,.2f}\n"
                                f"Interest Rate: {interest_rate}%\n"
                                f"Duration: {months} months\n"
                                f"Total Interest: ₹{interest:,.2f}\n"
                                f"Final Amount: ₹{total:,.2f}"
                            )
                            if send_sms(phone, message):
                                st.success("Investment added and SMS notification sent!")
                            else:
                                st.warning("Investment added but SMS notification failed.")
                    else:
                        st.success("Investment added successfully!")

                    conn.close()
                else:
                    st.warning("Please enter a valid amount!")

elif page == "Reports":
    st.title("Investment Reports")

    conn = sqlite3.connect('investments.db')
    users_df = pd.read_sql_query("SELECT * FROM users", conn)

    user_options = {"All Users": None}
    user_options.update({f"{row['name']} ({row['mobile']})": row['user_id']
                        for _, row in users_df.iterrows()})

    selected_user_name = st.selectbox("Select User", list(user_options.keys()))
    selected_user_id = user_options[selected_user_name]

    if selected_user_id:
        investments_df = pd.read_sql_query("""
            SELECT i.*, u.name
            FROM investments i
            JOIN users u ON i.user_id = u.user_id
            WHERE i.user_id = ?
        """, conn, params=(selected_user_id,))
    else:
        investments_df = pd.read_sql_query("""
            SELECT i.*, u.name
            FROM investments i
            JOIN users u ON i.user_id = u.user_id
        """, conn)

    conn.close()

    if not investments_df.empty:
        investments_df['total_interest'] = investments_df.apply(
            lambda row: calculate_interest(row['amount'], row['interest_rate'], row['months']),
            axis=1
        )
        investments_df['total_amount'] = investments_df['amount'] + investments_df['total_interest']

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Investment", f"₹{investments_df['amount'].sum():,.2f}")
        with col2:
            st.metric("Total Interest", f"₹{investments_df['total_interest'].sum():,.2f}")
        with col3:
            st.metric("Total Amount", f"₹{investments_df['total_amount'].sum():,.2f}")

        investments_df['date'] = pd.to_datetime(investments_df['date'])
        fig = px.line(investments_df, x='date', y=['amount', 'total_amount'],
                     title='Investment Timeline',
                     labels={'value': 'Amount (₹)', 'date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Investment Details")
        st.dataframe(
            investments_df[[
                'name', 'date', 'amount', 'interest_rate', 'months',
                'total_interest', 'total_amount'
            ]].sort_values('date', ascending=False)
        )
    else:
        st.info("No investments recorded yet.")