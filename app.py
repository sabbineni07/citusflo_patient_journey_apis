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
    db.create_all()
    
    # Create admin user if it doesn't exist
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@hospital.com',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created: username=admin, password=admin123")
    
    print("Database initialized successfully!")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
