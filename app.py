from flask import Flask, request, jsonify, flash, render_template, redirect, url_for
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from bson.objectid import ObjectId
from datetime import datetime
import config, bcrypt
from pymongo.errors import DuplicateKeyError

app = Flask(__name__)
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
            return redirect(url_for("dashboard"))
        else:
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    
    return render_template("dashboard.html", message=current_user.username)

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
                    "timestamp": datetime.now()    
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
                "timestamp": datetime.now()
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

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)