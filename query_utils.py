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
    
    