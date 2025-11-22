#!/usr/bin/env python3
"""
Script to test database connection and query users table
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

# Database connection details
DB_CONFIG = {
    'host': 'production-citusflo-patient-db.c8v468m8gv2i.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'patient_journey',
    'user': 'postgres',
    'password': 'Citusflo123'
}

def test_connection():
    """Test database connection and query users table"""
    try:
        print("🔌 Attempting to connect to database...")
        print(f"   Host: {DB_CONFIG['host']}")
        print(f"   Database: {DB_CONFIG['database']}")
        print(f"   User: {DB_CONFIG['user']}\n")
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Successfully connected to database!\n")
        
        # Create cursor with dictionary-like results
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query users table
        print("📊 Querying users table...")
        cursor.execute("""
            SELECT 
                id,
                username,
                email,
                first_name,
                last_name,
                role,
                facility_id,
                is_active,
                created_at,
                updated_at
            FROM users
            ORDER BY id
        """)
        
        users = cursor.fetchall()
        
        print(f"\n📋 Found {len(users)} user(s) in the database:\n")
        print("=" * 100)
        
        if users:
            # Print header
            print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Name':<25} {'Role':<10} {'Active':<8} {'Facility ID':<12}")
            print("-" * 100)
            
            # Print each user
            for user in users:
                full_name = f"{user['first_name']} {user['last_name']}"
                print(f"{user['id']:<5} {user['username']:<20} {user['email']:<30} {full_name:<25} {user['role']:<10} {str(user['is_active']):<8} {str(user['facility_id'] or 'N/A'):<12}")
        else:
            print("No users found in the database.")
        
        print("=" * 100)
        
        # Also show detailed information
        if users:
            print("\n📝 Detailed User Information:\n")
            for i, user in enumerate(users, 1):
                print(f"User #{i}:")
                print(f"  ID: {user['id']}")
                print(f"  Username: {user['username']}")
                print(f"  Email: {user['email']}")
                print(f"  Full Name: {user['first_name']} {user['last_name']}")
                print(f"  Role: {user['role']}")
                print(f"  Facility ID: {user['facility_id'] or 'None'}")
                print(f"  Active: {user['is_active']}")
                print(f"  Created: {user['created_at']}")
                print(f"  Updated: {user['updated_at']}")
                print()
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        print("✅ Database connection closed successfully.")
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print("\nPossible issues:")
        print("  - Database might not be accessible from this machine (security group restrictions)")
        print("  - Network connectivity issues")
        print("  - Incorrect credentials")
        return False
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)



