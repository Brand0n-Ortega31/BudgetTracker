import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/budget_tracker")