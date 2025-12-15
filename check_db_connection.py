#!/usr/bin/env python3
"""
Script to test database connection and query users table
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys
import getpass

# Database connection details
DB_CONFIG = {
    'host': 'production-patient-db.c8v468m8gv2i.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'patient_journey',
    'user': 'postgres',
    'password': os.getenv('DB_PASSWORD', ''),
    # AWS RDS requires SSL for external connections
    'sslmode': 'require',
    'connect_timeout': 10
}

# If password not in environment variable, prompt for it
if not DB_CONFIG['password']:
    DB_CONFIG['password'] = getpass.getpass('Enter database password: ')

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
        error_msg = str(e)
        print(f"❌ Connection failed: {e}")
        print("\nPossible issues:")
        
        if "password authentication failed" in error_msg.lower():
            print("  - ❌ Incorrect password")
            print("  - 💡 The password is randomly generated during deployment")
            print("  - 💡 See instructions below to reset or retrieve the password")
        elif "no pg_hba.conf entry" in error_msg.lower() or "no encryption" in error_msg.lower():
            print("  - ❌ SSL connection required")
            print("  - 💡 This script now uses SSL mode 'require'")
        elif "timeout" in error_msg.lower():
            print("  - ❌ Connection timeout")
            print("  - 💡 Check security group rules allow your IP (96.255.65.79)")
            print("  - 💡 Verify network connectivity")
        else:
            print("  - Database might not be accessible from this machine (security group restrictions)")
            print("  - Network connectivity issues")
            print("  - Incorrect credentials")
        
        print("\n📋 Troubleshooting:")
        print("  1. Verify password:")
        print("     - Option A: Reset password via AWS Console (RDS → Modify → Change Master Password)")
        print("     - Option B: Check deployment logs for generated password")
        print("  2. Verify security group allows your IP: 96.255.65.79/32")
        print("  3. Set password as environment variable:")
        print("     export DB_PASSWORD='your-password-here'")
        print("     python3 check_db_connection.py")
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





