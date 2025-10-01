# CitusFlo Patient Journey APIs

A comprehensive Flask-based REST API for managing patient journey records with JWT authentication, built with PostgreSQL database and containerized with Docker. This API is designed for healthcare case management and patient journey tracking with support for Angular frontend integration.

## 🚀 Features

- **🔐 JWT Authentication**: Complete authentication system with login, registration, profile management, and token refresh
- **👥 User Management**: User registration, profile updates, password changes, and role-based access
- **🏥 Patient Management**: Complete CRUD operations for patient records with case management focus
- **📊 Case Manager Records**: Specialized endpoints for case manager dashboard and reporting
- **🗄️ PostgreSQL Database**: Robust data storage with proper relationships and migrations
- **🐳 Docker Support**: Full containerization with development and production environments
- **🌐 CORS Configuration**: Properly configured for Angular frontend integration
- **🧪 Comprehensive Testing**: Unit tests, integration tests, and end-to-end tests
- **☁️ AWS Deployment**: Ready-to-deploy infrastructure with ECS Fargate
- **🔒 Security**: Password hashing, input validation, and secure authentication
- **📈 Database Migrations**: Flask-Migrate integration for schema management

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [API Endpoints](#-api-endpoints)
- [Database Schema](#-database-schema)
- [Docker Setup](#-docker-setup)
- [CORS Configuration](#-cors-configuration)
- [Angular Integration](#-angular-integration)
- [Testing](#-testing)
- [AWS Deployment](#-aws-deployment)
- [Development](#-development)
- [Contributing](#-contributing)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (if running locally)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd citusflo_patient_journey_apis
   ```

2. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run with Docker Compose (Recommended)**
   ```bash
   # For development
   docker-compose -f docker-compose.dev.yml up --build
   
   # For production
   docker-compose up --build
   ```

5. **Initialize the database**
   ```bash
   # Using Docker
   docker-compose -f docker-compose.dev.yml exec web flask init-db
   
   # Or locally
   flask init-db
   ```

6. **Access the application**
   - **Development API**: http://localhost:5001
   - **Production API**: http://localhost:5000
   - **Health Check**: http://localhost:5001/health

## 🔌 API Endpoints

### Authentication Endpoints

#### Register User
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepass123",
  "first_name": "John",
  "last_name": "Doe",
  "role": "user"
}
```

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@hospital.com",
    "first_name": "Admin",
    "last_name": "User",
    "role": "admin",
    "is_active": true,
    "created_at": "2025-10-01T13:12:34.380732",
    "updated_at": "2025-10-01T13:12:34.380735"
  }
}
```

#### Get Profile
```http
GET /api/auth/profile
Authorization: Bearer <access_token>
```

#### Update Profile
```http
PUT /api/auth/profile
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "first_name": "Johnny",
  "last_name": "Smith",
  "email": "johnny.smith@example.com"
}
```

#### Change Password
```http
POST /api/auth/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "current_password": "oldpass123",
  "new_password": "newpass123"
}
```

#### Validate Session
```http
POST /api/auth/validate-session
Authorization: Bearer <access_token>
```

#### Refresh Token
```http
POST /api/auth/refresh
Authorization: Bearer <access_token>
```

#### Get All Users
```http
GET /api/auth/users
```

#### Logout
```http
POST /api/auth/logout
Authorization: Bearer <access_token>
```

### Patient Management Endpoints

#### Create Patient
```http
POST /api/patients/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "caseManagerName": "John Smith",
  "phoneNumber": "+1234567890",
  "facilityName": "General Hospital",
  "patientName": "Jane Doe",
  "date": "2024-01-15",
  "referralReceived": true,
  "insuranceVerification": false,
  "familyAndPatientAware": true,
  "inPersonVisit": false,
  "dischargedFromFacility": false,
  "admitted": true,
  "careFollowUp": false,
  "formContent": "Patient requires follow-up care"
}
```

#### Get All Patients
```http
GET /api/patients/
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)
- `search`: Search term for patient name, case manager, or facility

**Response:**
```json
{
  "patients": [
    {
      "id": 1,
      "caseManagerName": "John Smith",
      "phoneNumber": "+1234567890",
      "facilityName": "General Hospital",
      "patientName": "Jane Doe",
      "date": "2024-01-15",
      "referralReceived": true,
      "insuranceVerification": false,
      "familyAndPatientAware": true,
      "inPersonVisit": false,
      "dischargedFromFacility": false,
      "admitted": true,
      "careFollowUp": false,
      "formContent": "Patient requires follow-up care",
      "created_by": 1,
      "created_at": "2025-10-01T13:27:14.699675",
      "updated_at": "2025-10-01T13:27:14.699677"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 10,
  "pages": 1
}
```

#### Get Patient by ID
```http
GET /api/patients/{id}
Authorization: Bearer <access_token>
```

#### Update Patient
```http
PUT /api/patients/{id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "caseManagerName": "John Smith Updated",
  "admitted": false,
  "careFollowUp": true,
  "formContent": "Updated form content"
}
```

#### Delete Patient
```http
DELETE /api/patients/{id}
Authorization: Bearer <access_token>
```

### Case Manager Records Endpoints

#### Get Case Manager Records
```http
GET /api/case-manager-records/
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)
- `search`: Search term for patient name, case manager, or facility
- `date_from`: Start date filter (ISO format)
- `date_to`: End date filter (ISO format)

**Example:**
```http
GET /api/case-manager-records/?page=1&per_page=100&date_from=2025-09-01T14:04:52.545Z&date_to=2025-10-01T14:04:52.545Z
Authorization: Bearer <access_token>
```

#### Get Case Manager Record by ID
```http
GET /api/case-manager-records/{id}
Authorization: Bearer <access_token>
```

#### Get Case Manager Statistics
```http
GET /api/case-manager-records/stats
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `date_from`: Start date filter (ISO format)
- `date_to`: End date filter (ISO format)

**Response:**
```json
{
  "stats": {
    "total_records": 25,
    "referral_received": 20,
    "insurance_verified": 18,
    "family_aware": 15,
    "in_person_visits": 12,
    "discharged": 8,
    "admitted": 10,
    "care_follow_up": 5,
    "referral_rate": 80.0,
    "insurance_verification_rate": 72.0,
    "admission_rate": 40.0
  }
}
```

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "patient-api"
}
```

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Patients Table (Updated Schema)
```sql
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    case_manager_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    facility_name VARCHAR(100) NOT NULL,
    patient_name VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    referral_received BOOLEAN DEFAULT FALSE,
    insurance_verification BOOLEAN DEFAULT FALSE,
    family_and_patient_aware BOOLEAN DEFAULT FALSE,
    in_person_visit BOOLEAN DEFAULT FALSE,
    discharged_from_facility BOOLEAN DEFAULT FALSE,
    admitted BOOLEAN DEFAULT FALSE,
    care_follow_up BOOLEAN DEFAULT FALSE,
    form_content TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🐳 Docker Setup

### Development Environment

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up --build

# Access services:
# - API: http://localhost:5001
# - Database: localhost:5433
```

### Production Environment

```bash
# Start production environment
docker-compose up --build

# Access services:
# - API: http://localhost:5000
# - Database: localhost:5432
# - Nginx: http://localhost:80
```

### Docker Commands

```bash
# Build image
docker build -t citusflo-patient-journey-api .

# Run container
docker run -p 5000:5000 --env-file .env citusflo-patient-journey-api

# View logs
docker-compose logs -f web

# Execute commands in container
docker-compose exec web flask shell

# Initialize database
docker-compose exec web flask init-db

# Run migrations
docker-compose exec web flask db upgrade
```

## 🌐 CORS Configuration

The API is configured with CORS support for Angular frontend integration.

### Development CORS Origins
- `http://localhost:4200` (Angular default)
- `http://localhost:3000` (React default)
- `http://127.0.0.1:4200`
- `http://127.0.0.1:3000`

### Environment Configuration
```bash
# Development
CORS_ORIGINS=http://localhost:4200,http://localhost:3000,http://127.0.0.1:4200,http://127.0.0.1:3000

# Production
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### CORS Features
- ✅ **Preflight Support**: OPTIONS requests handled automatically
- ✅ **Credentials Support**: JWT tokens work with CORS
- ✅ **Configurable Origins**: Environment-based origin configuration
- ✅ **Security**: Only specified origins allowed

## 🔧 Angular Integration

### Authentication Service Example
```typescript
@Injectable()
export class AuthService {
  private apiUrl = 'http://localhost:5001/api';
  
  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/auth/login`, {
      username, password
    });
  }
  
  getCaseManagerRecords(): Observable<CaseManagerRecordsResponse> {
    const token = localStorage.getItem('auth_token');
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    });
    
    return this.http.get<CaseManagerRecordsResponse>(
      `${this.apiUrl}/case-manager-records/`, 
      { headers }
    );
  }
}
```

### HTTP Interceptor (Recommended)
```typescript
@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const token = localStorage.getItem('auth_token');
    
    if (token) {
      req = req.clone({
        setHeaders: {
          'Authorization': `Bearer ${token}`
        }
      });
    }
    
    return next.handle(req);
  }
}
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test types
pytest -m unit                    # Unit tests only
pytest -m integration            # Integration tests only
pytest -m e2e                    # End-to-end tests only

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest app/tests/unit/test_auth.py
```

### Test Structure

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test API endpoints and database interactions
- **End-to-End Tests**: Test complete user workflows

### Test Data

The test suite includes:
- User authentication flows
- Patient CRUD operations
- Case manager records functionality
- Error handling scenarios
- Input validation
- Database operations

## ☁️ AWS Deployment

### Prerequisites

- AWS CLI configured
- Docker installed
- Appropriate AWS permissions

### Quick Deployment

```bash
# Make deployment script executable
chmod +x aws/deploy.sh

# Deploy to AWS
./aws/deploy.sh
```

### Manual Deployment Steps

1. **Create ECR Repository**
   ```bash
   aws ecr create-repository --repository-name citusflo-patient-journey-api --region us-east-1
   ```

2. **Build and Push Docker Image**
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   docker build -t citusflo-patient-journey-api .
   docker tag citusflo-patient-journey-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/citusflo-patient-journey-api:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/citusflo-patient-journey-api:latest
   ```

3. **Deploy Infrastructure**
   ```bash
   aws cloudformation deploy \
     --template-file aws/cloudformation-template.yaml \
     --stack-name citusflo-patient-journey-api-infrastructure \
     --capabilities CAPABILITY_IAM
   ```

4. **Update ECS Service**
   ```bash
   aws ecs update-service \
     --cluster production-citusflo-patient-cluster \
     --service production-citusflo-patient-service \
     --force-new-deployment
   ```

### AWS Architecture

The deployment includes:
- **ECS Fargate**: Container orchestration
- **Application Load Balancer**: Traffic distribution
- **RDS PostgreSQL**: Managed database
- **CloudWatch**: Logging and monitoring
- **Secrets Manager**: Secure configuration
- **VPC**: Network isolation

### Environment Variables

Set these in AWS Secrets Manager or ECS task definition:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT signing key
- `FLASK_ENV`: Environment (production)
- `CORS_ORIGINS`: Allowed CORS origins

## 🛠️ Development

### Project Structure

```
citusflo_patient_journey_apis/
├── app/
│   ├── __init__.py              # Flask app factory with CORS config
│   ├── models/                  # Database models
│   │   ├── user.py             # User model with authentication
│   │   └── patient.py          # Patient model (updated schema)
│   ├── routes/                 # API routes
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── patients.py        # Patient CRUD endpoints
│   │   └── case_manager_records.py  # Case manager dashboard endpoints
│   ├── services/              # Business logic
│   │   ├── auth_service.py    # Authentication service
│   │   └── patient_service.py # Patient management service
│   ├── utils/                 # Utilities
│   │   └── validators.py      # Input validation
│   └── tests/                 # Test suite
│       ├── unit/
│       ├── integration/
│       └── e2e/
├── migrations/                # Database migrations
├── aws/                      # AWS deployment files
├── docker-compose.yml        # Production Docker setup
├── docker-compose.dev.yml    # Development Docker setup
├── Dockerfile               # Docker image definition
├── requirements.txt         # Python dependencies
├── CORS-CONFIGURATION.md    # CORS setup guide
└── README.md               # This file
```

### Adding New Features

1. **Create Model** (if needed)
   ```python
   # app/models/new_model.py
   class NewModel(db.Model):
       # Define fields
   ```

2. **Create Migration**
   ```bash
   flask db migrate -m "Add new model"
   flask db upgrade
   ```

3. **Create Service**
   ```python
   # app/services/new_service.py
   class NewService:
       # Business logic
   ```

4. **Create Routes**
   ```python
   # app/routes/new_routes.py
   new_bp = Blueprint('new', __name__)
   # Define endpoints
   ```

5. **Register Blueprint**
   ```python
   # app/__init__.py
   app.register_blueprint(new_bp, url_prefix='/api/new')
   ```

6. **Add Tests**
   ```python
   # app/tests/unit/test_new_service.py
   # app/tests/integration/test_new_routes.py
   ```

7. **Update Documentation**

### Code Style

- Follow PEP 8
- Use type hints where appropriate
- Write comprehensive docstrings
- Include error handling
- Add logging for important operations

### Database Migrations

```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# Run code formatting
black app/

# Run linting
flake8 app/

# Run tests
pytest
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the API documentation
- Review the test cases for usage examples
- See CORS-CONFIGURATION.md for frontend integration help

## 📝 Changelog

### Version 2.0.0 (Current)
- ✅ **Updated Patient Model**: New schema focused on case management
- ✅ **Enhanced Authentication**: Complete JWT system with refresh tokens
- ✅ **Case Manager Records**: Specialized endpoints for dashboard functionality
- ✅ **CORS Configuration**: Proper Angular frontend integration
- ✅ **Database Migrations**: Flask-Migrate integration
- ✅ **Comprehensive Testing**: All endpoints tested and validated
- ✅ **Security Improvements**: Enhanced authentication and validation

### Version 1.0.0
- Initial release
- Basic user authentication with JWT
- Patient management CRUD operations
- PostgreSQL database integration
- Docker containerization
- Basic test suite
- AWS deployment configuration

## 🔑 Default Admin Credentials

For development and testing:
- **Username**: `admin`
- **Password**: `admin123`
- **Email**: `admin@hospital.com`
- **Role**: `admin`

> ⚠️ **Important**: Change these credentials in production!