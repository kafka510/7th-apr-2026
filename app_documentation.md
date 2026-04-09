# PEAK ENERGY - Comprehensive Application Documentation

## Table of Contents
1. [Application Overview](#application-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Project Structure](#project-structure)
4. [Database Models](#database-models)
5. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
6. [Features & Dashboards](#features--dashboards)
7. [API Endpoints](#api-endpoints)
8. [Installation & Setup](#installation--setup)
9. [Configuration](#configuration)
10. [Deployment](#deployment)
11. [User Management](#user-management)
12. [Data Management](#data-management)
13. [Troubleshooting](#troubleshooting)
14. [Maintenance](#maintenance)

---

## Application Overview

**PEAK ENERGY** is a comprehensive solar energy management and analytics platform designed for monitoring, analyzing, and reporting on solar power plant performance across multiple countries and portfolios.

### Key Features
- **Multi-Portfolio Management**: Manage solar assets across different countries and portfolios
- **Real-time Analytics**: KPI dashboards with performance metrics and forecasting
- **Role-Based Access Control**: Granular permissions for different user roles
- **Data Visualization**: Interactive charts and reports
- **CSV Data Import**: Bulk data upload capabilities
- **Time Series Analysis**: Historical data tracking and trend analysis

### Target Users
- **Administrators**: Full system access and user management
- **Operations & Maintenance (O&M)**: Asset monitoring and performance analysis
- **Management**: High-level reporting and strategic insights
- **Customers**: Portfolio-specific data access
- **Others**: Limited access based on requirements

---

## Architecture & Technology Stack

### Backend
- **Framework**: Django 5.2.4 (Python web framework)
- **Database**: PostgreSQL (Primary database)
- **Task Queue**: Celery with Redis (Background tasks)
- **Authentication**: Django's built-in authentication system
- **API**: RESTful APIs for data access

### Frontend
- **Templates**: Django Templates with Bootstrap 5.3.2
- **Charts**: Chart.js for data visualization
- **Date Pickers**: Flatpickr for date/time selection
- **Export**: HTML2PDF.js, XLSX.js for report generation

### Infrastructure
- **Web Server**: Gunicorn (WSGI server)
- **Reverse Proxy**: Nginx
- **Containerization**: Docker & Docker Compose
- **Environment**: Python 3.13.3

### Dependencies
```
Django>=4.2
gunicorn
psycopg2-binary
celery[redis]
django-celery-beat
django-celery-results
python-dotenv
pandas
pytz
requests
```

---

## Project Structure

```
django_web_app/
├── accounts/                 # User authentication app
│   ├── models.py            # User profile models
│   ├── views.py             # Authentication views
│   ├── urls.py              # Auth URL patterns
│   └── templates/           # Auth templates
├── main/                    # Core application
│   ├── models.py            # Database models
│   ├── views.py             # Business logic views
│   ├── urls.py              # URL routing
│   ├── permissions.py       # RBAC system
│   ├── context_processors.py # Template context
│   └── management/          # Custom commands
├── web_app/                 # Project settings
│   ├── settings.py          # Django settings
│   ├── urls.py              # Main URL configuration
│   └── wsgi.py              # WSGI application
├── templates/               # HTML templates
│   ├── base.html            # Base template
│   ├── main/                # Dashboard templates
│   └── accounts/            # Auth templates
├── static/                  # Static files
├── data/                    # CSV data files
├── requirements.txt          # Python dependencies
├── docker-compose.yml       # Docker configuration
├── dockerfile               # Docker image
└── manage.py                # Django management
```

---

## Database Models

### Core Models

#### AssetList
```python
class AssetList(models.Model):
    asset_code = models.CharField(max_length=255, primary_key=True)
    asset_name = models.CharField(max_length=255)
    capacity = models.DecimalField(max_digits=19, decimal_places=15)
    address = models.TextField()
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=19, decimal_places=15)
    longitude = models.DecimalField(max_digits=19, decimal_places=15)
    contact_person = models.TextField()
    contact_method = models.TextField()
    grid_connection_date = models.DateTimeField()
    asset_number = models.CharField(max_length=255)
    timezone = models.CharField(max_length=10)
```

#### UserProfile
```python
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('om', 'O&M'),
        ('customer', 'Customer'),
        ('management', 'Management'),
        ('others', 'Others'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    sites = models.ManyToManyField('AssetList', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Data Models

#### YieldData
- Monthly yield performance data
- DC/AC capacity tracking
- Performance ratio calculations
- Revenue loss analysis

#### BESSData
- Battery Energy Storage System data
- Charge/discharge cycles
- State of charge monitoring
- Temperature and humidity tracking

#### AOCData
- Areas of Concern tracking
- Asset-specific remarks
- Portfolio-level observations

#### Daily Data Models
- `ActualGenerationDailyData`: Daily generation kWh
- `ExpectedBudgetDailyData`: Daily budget expectations
- `BudgetGIIDailyData`: Daily budget GII data
- `ActualGIIDailyData`: Daily actual GII data

---

## Role-Based Access Control (RBAC)

### Permission System
The application implements a centralized RBAC system with the following features:

#### Roles
1. **Admin**: Full system access
2. **O&M**: Operations and maintenance access
3. **Customer**: Portfolio-specific access
4. **Management**: Strategic reporting access
5. **Others**: Limited access

#### Features & Permissions Matrix

| Feature | Admin | O&M | Customer | Management | Others |
|---------|-------|-----|----------|------------|--------|
| Portfolio Map | ✓ | ✗ | ✓ | ✓ | ✓ |
| KPI Dashboard | ✓ | ✗ | ✓ | ✗ | ✗ |
| Sales | ✓ | ✗ | ✓ | ✓ | ✗ |
| Yield Report | ✓ | ✓ | ✗ | ✓ | ✗ |
| PR Gap | ✓ | ✓ | ✗ | ✓ | ✗ |
| Revenue Loss | ✓ | ✓ | ✗ | ✓ | ✗ |
| Areas of Concern | ✓ | ✓ | ✗ | ✓ | ✗ |
| BESS Performance | ✓ | ✓ | ✗ | ✓ | ✗ |
| Minamata Typhoon | ✓ | ✗ | ✗ | ✓ | ✗ |
| IC Budget vs Expected | ✓ | ✗ | ✗ | ✓ | ✗ |
| Main Dashboard | ✓ | ✓ | ✓ | ✓ | ✓ |
| Generation Report | ✓ | ✗ | ✗ | ✓ | ✗ |
| Time Series Dashboard | ✓ | ✗ | ✗ | ✗ | ✗ |
| User Management | ✓ | ✗ | ✗ | ✗ | ✗ |

#### Implementation
- **`main/permissions.py`**: Centralized permission definitions
- **`main/context_processors.py`**: Template-level permission checks
- **`@feature_required`**: View-level permission decorator
- **Template Variables**: `permission_checks.feature_name` for UI control

---

## Features & Dashboards

### 1. Unified Operations Dashboard
**URL**: `/dashboard/`
**Access**: All authenticated users
**Features**:
- Portfolio overview with expandable hierarchy
- Country → Portfolio → Asset structure
- Real-time KPI metrics
- Interactive data visualization
- Export capabilities (PDF, Excel, CSV)

### 2. KPI Analytics Dashboard
**URL**: `/generation-report/`
**Access**: Admin, Management
**Features**:
- Performance ratio analysis
- Budget vs actual comparisons
- Forecasted generation calculations
- Multi-month date range selection
- Comprehensive reporting

### 3. Portfolio Map
**URL**: `/portfolio-map/`
**Access**: Admin, Customer, Management, Others
**Features**:
- Geographic asset visualization
- Interactive map with asset details
- Country and portfolio filtering
- Real-time asset status

### 4. Yield Report
**URL**: `/yield-report/`
**Access**: Admin, O&M, Management
**Features**:
- Monthly yield performance
- DC/AC capacity tracking
- Performance ratio analysis
- Historical trend analysis

### 5. BESS Performance
**URL**: `/bess-performance/`
**Access**: Admin, O&M, Management
**Features**:
- Battery storage analytics
- Charge/discharge efficiency
- State of charge monitoring
- Temperature and humidity tracking

### 6. User Management
**URL**: `/user-management/`
**Access**: Admin only
**Features**:
- User creation and management
- Role assignment
- Site access control
- Password reset functionality
- Multi-country site selection

---

## API Endpoints

### Data APIs
```
GET /api/map-data/                    # Asset mapping data
GET /api/yield-data/                  # Yield performance data
GET /api/bess-data/                   # BESS performance data
GET /api/aoc-data/                    # Areas of concern data
GET /api/ice-data/                    # ICE data
GET /api/minamata-string-loss-data/   # Minamata typhoon data
```

### Daily Data APIs
```
GET /api/actual-generation-daily/     # Daily generation data
GET /api/expected-budget-daily/       # Daily budget data
GET /api/budget-gii-daily/           # Daily budget GII data
GET /api/actual-gii-daily/           # Daily actual GII data
GET /api/ic-approved-budget-daily/   # IC approved budget data
```

### Time Series APIs
```
GET /api/time-series-data/           # Time series data with filtering
GET /api/sites/                      # Available sites
GET /api/devices/                    # Device information
GET /api/metrics/                    # Available metrics
```

### Authentication APIs
```
POST /accounts/login/                 # User login
POST /accounts/logout/                # User logout
POST /accounts/password-reset/        # Password reset
```

---

## Installation & Setup

### Prerequisites
- Python 3.13.3+
- PostgreSQL 12+
- Redis (for Celery)
- Docker & Docker Compose (optional)

### Local Development Setup

1. **Clone Repository**
```bash
git clone <repository-url>
cd django_web_app
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
Create `.env` file:
```env
SECRET_KEY=your-secret-key-here
POSTGRES_DB=peak_energy_db
POSTGRES_USER=peak_energy_user
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_URL=redis://localhost:6379
```

5. **Database Setup**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

6. **Run Development Server**
```bash
python manage.py runserver
```

### Docker Setup

1. **Build and Start Services**
```bash
docker-compose up --build
```

2. **Run Migrations**
```bash
docker-compose exec web python manage.py migrate
```

3. **Create Superuser**
```bash
docker-compose exec web python manage.py createsuperuser
```

---

## Configuration

### Django Settings (`web_app/settings.py`)

#### Database Configuration
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST'),
        'PORT': os.environ.get('POSTGRES_PORT'),
    }
}
```

#### Celery Configuration
```python
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379')
```

#### Static Files
```python
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
```

### Environment Variables
- `SECRET_KEY`: Django secret key
- `POSTGRES_*`: Database connection parameters
- `REDIS_URL`: Redis connection for Celery
- `DEBUG`: Development mode flag

---

## Deployment

### Production Deployment

1. **Environment Setup**
```bash
# Set production environment variables
export DEBUG=False
export SECRET_KEY=your-production-secret-key
```

2. **Static Files Collection**
```bash
python manage.py collectstatic
```

3. **Database Migration**
```bash
python manage.py migrate
```

4. **Gunicorn Configuration**
```bash
gunicorn web_app.wsgi:application --bind 0.0.0.0:8000
```

### Docker Production Deployment

1. **Build Production Image**
```bash
docker build -t peak-energy-app .
```

2. **Run with Docker Compose**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        alias /path/to/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## User Management

### User Roles & Permissions

#### Admin Role
- **Full System Access**: All features and data
- **User Management**: Create, edit, delete users
- **System Configuration**: Database management, settings
- **Data Import**: Bulk data upload capabilities

#### O&M Role
- **Asset Monitoring**: Real-time asset performance
- **Yield Analysis**: Performance ratio calculations
- **BESS Monitoring**: Battery storage analytics
- **Areas of Concern**: Issue tracking and reporting

#### Management Role
- **Strategic Reporting**: High-level performance metrics
- **Portfolio Analysis**: Multi-asset comparisons
- **Budget Analysis**: Financial performance tracking
- **KPI Dashboards**: Executive-level reporting

#### Customer Role
- **Portfolio Access**: Limited to assigned assets
- **Performance Data**: Asset-specific metrics
- **Sales Information**: Commercial data access

### User Creation Process

1. **Access User Management**
   - Navigate to `/user-management/`
   - Admin access required

2. **Fill User Details**
   - Username and email
   - Password (temporary)
   - Role selection

3. **Assign Sites**
   - Select countries (multiple selection supported)
   - Choose specific sites from selected countries
   - Use "Select All" options for bulk assignment

4. **User Activation**
   - User receives email with login credentials
   - Password reset link available for first login

### Password Management
- **Reset Links**: Admin can send password reset emails
- **Temporary Passwords**: Initial passwords for new users
- **Security**: CSRF protection and session management

---

## Data Management

### Data Import Process

#### CSV Import Command
```bash
python manage.py import_csv_data <filename> <model_name>
```

#### Supported Data Types
- **Yield Data**: Monthly performance metrics
- **BESS Data**: Battery storage information
- **AOC Data**: Areas of concern
- **Map Data**: Asset geographic information
- **Daily Data**: Generation and budget data

#### Data Validation
- **Format Checking**: CSV structure validation
- **Data Type Validation**: Numeric and date field validation
- **Duplicate Prevention**: Unique constraint enforcement
- **Error Logging**: Import failure tracking

### Data Models Overview

#### YieldData
- Monthly performance tracking
- DC/AC capacity monitoring
- Performance ratio calculations
- Revenue analysis

#### BESSData
- Battery storage metrics
- Charge/discharge cycles
- Environmental monitoring
- Efficiency calculations

#### Daily Data Models
- **ActualGenerationDailyData**: Real generation data
- **ExpectedBudgetDailyData**: Budget expectations
- **BudgetGIIDailyData**: Budget GII information
- **ActualGIIDailyData**: Actual GII measurements

### Data Export Capabilities

#### Report Formats
- **PDF**: Professional reports with watermarks
- **Excel**: Spreadsheet format for analysis
- **CSV**: Raw data export
- **Print**: Browser-based printing

#### Export Features
- **Filtered Data**: Date range and asset filtering
- **Customizable Layouts**: Template-based formatting
- **Watermarking**: Branded document generation
- **Batch Processing**: Multiple report generation

---

## Troubleshooting

### Common Issues

#### CSRF Errors
**Problem**: `Forbidden (403) CSRF cookie not set`
**Solutions**:
1. Ensure `{% csrf_token %}` in forms
2. Check `@ensure_csrf_cookie` decorator usage
3. Verify CSRF settings in `settings.py`
4. Clear browser cookies and cache

#### Database Connection Issues
**Problem**: PostgreSQL connection failures
**Solutions**:
1. Verify database credentials in `.env`
2. Check PostgreSQL service status
3. Confirm network connectivity
4. Validate database permissions

#### Permission Errors
**Problem**: Access denied to features
**Solutions**:
1. Check user role assignments
2. Verify permission configurations
3. Review `permissions.py` settings
4. Clear user session cache

#### Static Files Not Loading
**Problem**: CSS/JS files not accessible
**Solutions**:
1. Run `python manage.py collectstatic`
2. Check `STATIC_ROOT` configuration
3. Verify Nginx static file serving
4. Clear browser cache

### Debug Mode

#### Development Debugging
```python
# settings.py
DEBUG = True
ALLOWED_HOSTS = ['*']
```

#### Logging Configuration
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

### Performance Optimization

#### Database Optimization
- **Indexing**: Add database indexes for frequent queries
- **Query Optimization**: Use `select_related()` and `prefetch_related()`
- **Connection Pooling**: Configure PostgreSQL connection pooling

#### Caching Strategy
- **Redis Caching**: Implement Redis for session storage
- **Query Caching**: Cache expensive database queries
- **Static File Caching**: Configure browser caching headers

---

## Maintenance

### Regular Maintenance Tasks

#### Daily Tasks
- **Log Review**: Check application logs for errors
- **Database Backup**: Automated PostgreSQL backups
- **Performance Monitoring**: System resource usage

#### Weekly Tasks
- **Data Validation**: Verify data integrity
- **User Access Review**: Audit user permissions
- **Security Updates**: Apply security patches

#### Monthly Tasks
- **Database Optimization**: Analyze and optimize queries
- **Backup Testing**: Verify backup restoration
- **Performance Analysis**: Review system performance metrics

### Backup Procedures

#### Database Backup
```bash
# PostgreSQL backup
pg_dump peak_energy_db > backup_$(date +%Y%m%d).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump peak_energy_db > $BACKUP_DIR/backup_$DATE.sql
```

#### File System Backup
```bash
# Application files backup
tar -czf app_backup_$(date +%Y%m%d).tar.gz django_web_app/

# Static files backup
tar -czf static_backup_$(date +%Y%m%d).tar.gz staticfiles/
```

### Monitoring & Alerts

#### System Monitoring
- **CPU Usage**: Monitor server CPU utilization
- **Memory Usage**: Track RAM consumption
- **Disk Space**: Monitor storage capacity
- **Network Traffic**: Track bandwidth usage

#### Application Monitoring
- **Error Rates**: Monitor application errors
- **Response Times**: Track API response times
- **User Activity**: Monitor user engagement
- **Database Performance**: Track query performance

### Security Maintenance

#### Regular Security Tasks
- **Password Updates**: Regular password rotation
- **Access Reviews**: Periodic permission audits
- **Security Patches**: Apply Django and dependency updates
- **SSL Certificate Renewal**: Maintain HTTPS certificates

#### Security Best Practices
- **Environment Variables**: Use `.env` for sensitive data
- **CSRF Protection**: Ensure CSRF tokens on all forms
- **Input Validation**: Validate all user inputs
- **SQL Injection Prevention**: Use Django ORM properly

---

## Conclusion

This comprehensive documentation provides a complete overview of the PEAK ENERGY application, including its architecture, features, setup procedures, and maintenance guidelines. The application is designed to be scalable, secure, and user-friendly, with robust role-based access control and comprehensive data management capabilities.

For additional support or questions, refer to the individual component documentation files or contact the development team.

---

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Maintained By**: Development Team 