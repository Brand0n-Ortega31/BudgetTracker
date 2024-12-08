from flask import Flask, request, jsonify, flash, render_template, redirect, url_for
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from bson.objectid import ObjectId
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from query_utils import current_month_expenses
from bson.json_util import dumps

import config, bcrypt

app = Flask(__name__, static_folder='static')
app.config["MONGO_URI"] = config.MONGO_URI
app.config["SECRET_KEY"] = 'thisisasecretkey'
app.config['SESSION_COOKIE_SECURE'] = False 
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
mongo = PyMongo(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    user_db = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user_db:
        return User(str(user_db["_id"]), user_db["username"])
    return None
        
@app.route("/register", methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return redirect(url_for("register"))
        
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        try:
            mongo.db.users.insert_one({
                "username": username, 
                "password": hashed_password
            })
            return redirect(url_for("login"))
        except DuplicateKeyError:
            return redirect(url_for("register"))
    
    return render_template('register.html')

@app.route("/", methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
    
        user = mongo.db.users.find_one({"username": username})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            user = User(str(user["_id"]), user["username"])
            login_user(user)
            
            profile = mongo.db.profiles.find_one({"user_id": user.id})
            if not profile or not all([
                profile.get('after_tax_income'),
                profile.get("frequency"),
                profile.get("budgeting_rule")
            ]):
                flash("Please Complete your Profile information.")
                return redirect(url_for('profile'))
            
            return redirect(url_for("dashboard"))
        else:
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    expenses = current_month_expenses(current_user.id, mongo.db)
    total_expense = sum(expense["amount"] for expense in expenses)
    
    category_breakdown = {}
    for expense in expenses:
        category = expense["category"]
        category_breakdown[category] = category_breakdown.get(category, 0) + expense["amount"]
        
    #TODO print out the value of sum above before it updates to round how to round off the value to the second decimal point
        
    print(f"[DEBUG] Category Breakdown: {category_breakdown}")
    
    pie_chart = {
        "labels" : list(category_breakdown.keys()),
        "values" : list(category_breakdown.values())
    }
    
    
    print(f"[DEBUG] Pie Chart: {pie_chart}")
    return render_template("dashboard.html", total_expense = total_expense, pie_chart = pie_chart )

@app.route("/adding_expense", methods=['GET','POST'])
@login_required
def adding_expense():
    expense_submission = ["Food","Transportation","Utilities","Rent","Entertainment","Credit Card Payment"]

    if request.method == 'POST':
        if "edit_expense" in request.form:
            expense_id = request.form.get("edit_expense")
            description = request.form.get(f"expense_description_{expense_id}")
            category = request.form.get(f"expense_category_{expense_id}")
            amount = request.form.get(f"expense_amount_{expense_id}")

            try:
                amount_converted = float(amount)
            except ValueError:
                return redirect(url_for("adding_expense"))
            
            if not description or not category:
                return redirect(url_for("adding_expense"))
            
            mongo.db.expenses.update_one(
                {"_id": ObjectId(expense_id)},
                {"$set": {
                    "description": description,
                    "category": category,
                    "amount": amount_converted,
                    "timestamp": datetime.now(timezone.utc)    
                }}
            )

            return redirect(url_for("adding_expense"))
        else:
            amount = request.form.get('amount')
            description = request.form.get('description')
            category = request.form.get('category')

            try: 
                amount_converted = float(amount)
            except ValueError:
                return redirect(url_for("adding_expense"))
            
            if not description or not category:
                return redirect(url_for("adding_expense"))

            mongo.db.expenses.insert_one({
                "user_id": current_user.id,
                "amount": amount_converted,
                "description": description,
                "category": category,
                "timestamp": datetime.now(timezone.utc)
            })
            return redirect(url_for("adding_expense"))
        
    expenses = mongo.db.expenses.find({"user_id": current_user.id})
    expenses_list = list(expenses)
        
    return render_template("adding_expense.html",  categories=expense_submission, expenses=expenses_list)

@app.route("/get-expenses", methods=["GET"])
@login_required
def get_expenses():
    user_id = current_user.id
    expenses = list(mongo.db.expenses.find({"user_id": user_id}))
    for expense in expenses:
        expense["_id"] = str(expense["_id"])
    return jsonify(expenses)

# @app.route("/api/expenses", methods=["GET"])
# @login_required
# def get_month_expenses():

#     user_id = current_user.id
#     today = datetime.now(timezone.utc)
#     current_month_start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)

#     if today.month == 12:
#         next_month_start = datetime(today.year + 1, 1, 1, tzinfo=timezone.utc)
#     else:
#         next_month_start = datetime(today.year, today.month + 1, 1, tzinfo=timezone.utc)

#     expenses = list(mongo.db.expenses.find({
#         "user_id": ObjectId(user_id),
#         "timestamp": {"$gte": current_month_start, "$lt": next_month_start}
#     }))

#     return dumps(expenses), 200  # JSON response

@app.route('/profile', methods=["GET",'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            after_tax_income = float(request.form.get('after_tax_income'))
            frequency = request.form.get('frequency')
            budget_rule = request.form.get('budget_rule')
            
            custom_needs = None
            custom_wants = None
            custom_savings = None
            
            if budget_rule == 'custom':
                custom_needs = request.form.get('custom_needs', default=0).strip()
                custom_wants = request.form.get('custom_wants', default=0).strip()
                custom_savings = request.form.get('custom_savings', default=0).strip()
                
                try:
                    custom_needs = int(custom_needs)
                    custom_wants = int(custom_wants)
                    custom_savings = int(custom_savings)
                except ValueError:
                    flash("Custom perventages must be integers.", "danger")
                    return redirect(url_for("profile"))
                
                if custom_needs + custom_wants + custom_savings != 100:
                    flash("Custom budget rule must total 100.", "danger")
                    return redirect(url_for("profile"))
            
            profile_data = {
                "after_tax_income": after_tax_income,
                "frequency": frequency,
                "budget_rule":budget_rule,
                "custom_needs": custom_needs,
                "custom_wants": custom_wants,
                "custom_savings":custom_savings
            }   
            
            mongo.db.users.update_one(
                {"_id":ObjectId(current_user.id)},
                {"$set": {"profile": profile_data}},
                upsert=True
            ) 
            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile"))
    
        except Exception as e:
            flash(f"An error occurred: {e}", "danger")
            
    user_data = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
    profile = user_data.get('profile', {
        "after_tax_income": "",
        "frequency": "",
        "budget_rule": "",
        "custom_needs": "",
        "custom_wants": "",
        "custom_savings": ""
    })
    
    return render_template('profile.html', profile = profile)
        
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)