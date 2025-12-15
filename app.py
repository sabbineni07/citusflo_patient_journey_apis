from app import create_app, db
from app.models.user import User
from app.models.patient import Patient

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Patient': Patient}

@app.cli.command()
def init_db():
    """Initialize the database with sample data"""
    from app.models.role import Role
    
    db.create_all()
    
    # Seed roles first
    predefined_roles = [
        {'name': 'super_admin', 'description': 'Super Administrator with full system access and management'},
        {'name': 'admin', 'description': 'Administrator with full system access'},
        {'name': 'clinician', 'description': 'Clinical staff member'},
        {'name': 'case_manager', 'description': 'Case manager responsible for patient coordination'}
    ]
    for role_data in predefined_roles:
        Role.get_or_create(role_data['name'], role_data['description'])
    print("✅ Roles seeded successfully")
    
    # # Create default super admin user if it doesn't exist
    # admin_user = User.query.filter_by(username='citusflo_admin').first()
    # if not admin_user:
    #     # Get super_admin role_id
    #     super_admin_role = Role.query.filter_by(name='super_admin').first()
    #     if not super_admin_role:
    #         # If super_admin role doesn't exist, create it
    #         super_admin_role = Role.get_or_create('super_admin', 'Super Administrator with full system access and management')
    #
    #     admin_user = User(
    #         username='**********',
    #         email='account@citusflo.com',
    #         first_name='CitusFlo',
    #         last_name='Admin',
    #         role='super_admin',  # Kept for backward compatibility
    #         role_id=super_admin_role.id  # Set role_id for proper role relationship
    #     )
    #     # set password
    #     admin_user.set_password('********')
    #     db.session.add(admin_user)
    #     db.session.commit()
    #     print("Super admin user created: username=********, password=********")
    #     print(f"Super admin user role_id: {super_admin_role.id}")
    
    print("Database initialized successfully!")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
