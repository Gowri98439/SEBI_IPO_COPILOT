import asyncio
import sqlite3
import os

DB_PATH = "ipo_copilot.db"

def assert_count(cursor, table, expected_min):
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"Table {table}: {count} rows (expected >= {expected_min})")
    if count < expected_min:
        raise AssertionError(f"Expected at least {expected_min} rows in {table}, got {count}")

def main():
    if not os.path.exists(DB_PATH):
        raise Exception(f"Database {DB_PATH} not found!")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- Database Persistence Audit ---")
    try:
        assert_count(cursor, "users", 1)
        assert_count(cursor, "companies", 1)
        assert_count(cursor, "workspaces", 1)
        assert_count(cursor, "documents", 1)
        assert_count(cursor, "validation_results", 1)
        assert_count(cursor, "compliance_checks", 1)
        
        print("\nAll database persistence assertions passed!")
    except Exception as e:
        print(f"Audit failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
