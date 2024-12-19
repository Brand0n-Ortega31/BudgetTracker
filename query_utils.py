from datetime import datetime, timezone, timedelta
from bson.objectid import ObjectId

def current_month_expenses(user_id, db):
    '''we are grabbing the users expense so we 
    can display their total per month
    
    (user_id) : ID of current user
    (db) : database object (MongoDB)
    
    Returns: List of expense of current month
    '''  
    user_timezone = timezone(timedelta(hours=-5))
    today = datetime.now(user_timezone)
    current_month_beginning = datetime(today.year, today.month, 1, tzinfo=user_timezone)
    
    if today.month == 12:
        next_month_beginning = datetime(today.year + 1, 1, 1, tzinfo=user_timezone)
    else: 
        next_month_beginning = datetime(today.year, today.month + 1, 1, tzinfo=user_timezone)
    
    current_month_beginning_utc = current_month_beginning.astimezone(timezone.utc)
    next_month_beginning_utc = next_month_beginning.astimezone(timezone.utc)
    
    expenses = list(db.expenses.find({
        "user_id": user_id,
        "timestamp": {"$gte": current_month_beginning_utc,
                      "$lt": next_month_beginning_utc}
    })) 
    
    return expenses
    

def applying_budget_rule(profile):
    after_tax_income = profile.get("after_tax_income")
    budget_rule = profile.get("budget_rule")
    frequency = profile.get("frequency")

    if frequency == "weekly":
        monthly_income = after_tax_income * 52 / 12
    elif frequency == "biweekly":
        monthly_income = after_tax_income * 26 / 12
    elif frequency == "semimonthly":
        monthly_income = after_tax_income * 2
    else:
        monthly_income = after_tax_income

    if budget_rule == "custom":
        custom_needs = profile.get("custom_needs")
        custom_wants = profile.get("custom_wants")
        custom_savings = profile.get("custom_savings")
        
        needs_percent = custom_needs
        wants_percent = custom_wants
        savings_percent = custom_savings
    else:
        needs_percent, wants_percent, savings_percent = map(int, budget_rule.split("/"))

    # We can turn the income to cents and calculate from there
    total_income_cents = int(monthly_income * 100)
    needs_cents = total_income_cents * needs_percent // 100
    wants_cents = total_income_cents * wants_percent // 100
    savings_cents = total_income_cents * savings_percent // 100
    
    allocated_cents = needs_cents + wants_cents + savings_cents
    remainder_cents = total_income_cents - allocated_cents

    needs_cents += remainder_cents

    needs = needs_cents / 100
    wants = wants_cents / 100
    savings = savings_cents / 100

    return {
        "needs": f"{needs:.2f}",
        "wants": f"{wants:.2f}",
        "savings": f"{savings:.2f}",
        "monthly_income": f"{monthly_income:.2f}"
    }