import sqlite3
import os
from seed_data import init_db, seed_data

DB_PATH = "database/medical_knowledge.db"

def reset_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing database: {DB_PATH}")
    
    init_db()
    seed_data()
    print("Database reset and seeded successfully.")

if __name__ == "__main__":
    reset_db()
