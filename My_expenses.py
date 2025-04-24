import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# ---------- File Persistence ----------
def load_users():
    if os.path.exists("users.json") and os.path.getsize("users.json") > 0:
        with open("users.json", "r") as f:
            try:
                raw = json.load(f)
                for user in raw:
                    df = pd.DataFrame(raw[user].get('expenses', []))
                    if df.empty:
                        df = pd.DataFrame(columns=['Date', 'Description', 'Amount'])
                    raw[user]['expenses'] = df
                return raw
            except json.JSONDecodeError:
                print("⚠️ Warning: Failed to load JSON, file might be corrupted.")
                return {}
    return {}


def serialize_expenses(expenses_df):
    df_copy = expenses_df.copy()
    
    # Ensure Date is string (ISO)
    if 'Date' in df_copy.columns:
        df_copy['Date'] = pd.to_datetime(df_copy['Date'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Replace NaNs with empty strings for JSON compatibility
    df_copy = df_copy.fillna("")
    
    return df_copy.to_dict(orient='records')
def save_users():
    save_data = {}
    for username, data in st.session_state.users.items():
        expenses_data = serialize_expenses(data['expenses'])

        save_data[username] = {
            'password': data['password'],
            'age': data['profile'].age,
            'balance': float(data['profile'].balance),
            'expenses': expenses_data
        }

    with open("users.json", "w") as f:
        json.dump(save_data, f, indent=2)


# ---------- Person Class ----------
class Person:
    def __init__(self, username, age, balance):
        self.username = username
        self.age = age
        self.balance = balance

    def display_info(self):
        st.subheader("👤 Profile")
        st.write(f"**Username:** {self.username}")
        st.write(f"**Age:** {self.age}")
        st.write(f"**Current Balance:** ₹{self.balance:.2f}")

    def update_balance(self, amount):
        self.balance += amount

# ---------- Initialization ----------
if 'users' not in st.session_state:
    raw_users = load_users()
    users = {}
    for username, info in raw_users.items():
        users[username] = {
            'password': info['password'],
            'profile': Person(username, info['age'], info['balance']),
            'expenses': info['expenses']
        }
    st.session_state.users = users

if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

# ---------- UI ----------
st.title("💸 Expense Tracker (Login + Save)")

# Sign Up
with st.expander("🆕 Create Account"):
    new_username = st.text_input("Username", key="signup_username")
    new_password = st.text_input("Password", type="password", key="signup_password")
    new_age = st.number_input("Your Age", min_value=0, step=1, key="signup_age")
    new_balance = st.number_input("Initial Balance ₹", step=0.01, key="signup_balance")

    if st.button("Create Account", key="create_btn"):
        if new_username in st.session_state.users:
            st.warning("Username already exists.")
        else:
            st.session_state.users[new_username] = {
                'password': new_password,
                'profile': Person(new_username, new_age, new_balance),
                'expenses': pd.DataFrame(columns=['Date', 'Description', 'Amount'])
            }
            save_users()
            st.success("Account created successfully!")

# Login
if st.session_state.logged_in_user is None:
    st.subheader("🔐 Login")
    username = st.text_input("Login Username", key="login_user")
    password = st.text_input("Login Password", type="password", key="login_pass")

    if st.button("Login", key="login_btn"):
        user = st.session_state.users.get(username)
        if user and user['password'] == password:
            st.session_state.logged_in_user = username
            st.success(f"Welcome back, {username}!")
        else:
            st.error("Invalid username or password")

# ---------- Main App ----------
if st.session_state.logged_in_user:
    user_data = st.session_state.users[st.session_state.logged_in_user]
    person = user_data['profile']
    expenses = user_data['expenses']

    person.display_info()

    # Tabs for app sections
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Expense", "💳 Add Credit", "📈 Graph", "📋 Transactions"])

    # ➕ Add Expense
    with tab1:
        with st.form("expense_form"):
            st.subheader("➕ Add Expense")
            date1 = st.date_input("Date", datetime.today(), key="exp_date")
            date = pd.to_datetime(date1)
            description = st.text_input("Description", key="exp_desc")
            amount = st.number_input("Amount Spent", min_value=0.0, format="%.2f", key="exp_amount")
            submit = st.form_submit_button("Add Expense")
            if submit:
                new_exp = pd.DataFrame({
                    'Date': [str(date)],
                    'Description': [description],
                    'Amount': [-amount]
                })
                user_data['expenses'] = pd.concat([user_data['expenses'], new_exp], ignore_index=True)
                person.update_balance(-amount)
                save_users()
                st.success("Expense recorded!")

    # 💳 Add Credit
    with tab2:
        with st.form("credit_form"):
            st.subheader("💳 Add Credit")
            date = st.date_input("Date", datetime.today(), key="credit_date")
            source = st.text_input("Credit Source", key="credit_desc")
            amount = st.number_input("Amount Credited", min_value=0.0, format="%.2f", key="credit_amount")
            submit = st.form_submit_button("Add Credit")
            if submit:
                new_credit = pd.DataFrame({
                    'Date': [str(pd.to_datetime(date))],
                    'Description': [source],
                    'Amount': [amount]
                })
                user_data['expenses'] = pd.concat([user_data['expenses'], new_credit], ignore_index=True)
                person.update_balance(amount)
                save_users()
                st.success("Credit added successfully!")

    # 📈 Graph
    with tab3:
        st.subheader("📈 Spending & Credit Over Time")
        df = user_data['expenses']
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df_sorted = df.sort_values('Date')
            st.line_chart(df_sorted.groupby('Date')['Amount'].sum().cumsum())
            st.bar_chart(df_sorted.groupby('Description')['Amount'].sum())
        else:
            st.info("No transactions yet.")

    # 📋 All Transactions
    with tab4:
        st.subheader("📋 All Transactions")
        st.dataframe(user_data['expenses'].sort_values('Date', ascending=False))

    # 🔚 Logout
    if st.button("Logout", key="logout_btn"):
        st.session_state.logged_in_user = None
        st.success("Logged out!")
