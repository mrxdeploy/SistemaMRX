from app import create_app, db
import os
from dotenv import load_dotenv

load_dotenv()

app = create_app()
with app.app_context():
    print("Creating tables...")
    try:
        db.create_all()
        print("Tables created.")
    except Exception as e:
        print(f"Error: {e}")
