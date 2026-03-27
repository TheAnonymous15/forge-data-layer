# ForgeForth Africa - Data Layer Service

**The Single Source of Truth for All Platform Data**

The Data Layer is the centralized database microservice that owns and manages ALL databases for the ForgeForth Africa platform. No other service directly accesses databases - they all communicate through this service via REST API.

## Why a Centralized Data Layer?

1. **Single Source of Truth**: All data operations go through one service
2. **Security**: Database credentials only exist in one place
3. **Consistency**: Business rules enforced at one point
4. **Scalability**: Can scale database and API independently
5. **Compliance**: Centralized audit logging for POPIA/GDPR
6. **Flexibility**: Can switch databases without changing other services

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ForgeForth Africa Platform                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Website  │  │  Talent  │  │   Org    │  │  Admin   │        │
│  │ :8000    │  │  Portal  │  │  Portal  │  │  Portal  │        │
│  │          │  │  :9003   │  │  :9004   │  │  :9001   │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │               │
│       └─────────────┴──────┬──────┴─────────────┘               │
│                            │                                     │
│                    ┌───────▼───────┐                            │
│                    │  Data Layer   │                            │
│                    │    :9010      │                            │
│                    │  REST API     │                            │
│                    └───────┬───────┘                            │
│                            │                                     │
│       ┌────────────────────┼────────────────────┐               │
│       │                    │                    │               │
│  ┌────▼────┐          ┌────▼────┐          ┌────▼────┐         │
│  │ SQLite  │    OR    │  Neon   │    OR    │ cPanel  │         │
│  │  (Dev)  │          │ Postgres│          │ Postgres│         │
│  └─────────┘          └─────────┘          └─────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

```
data.forgeforthafrica.com (Port 9010)
├── /api/v1/users/         - User CRUD and authentication
├── /api/v1/profiles/      - Talent profile operations
├── /api/v1/organizations/ - Organization operations
├── /api/v1/opportunities/ - Job/opportunity operations
├── /api/v1/applications/  - Application tracking
├── /api/v1/tokens/        - Token management
├── /api/v1/audit/         - Audit logs
├── /api/docs/             - Swagger documentation
├── /api/redoc/            - ReDoc documentation
└── /health/               - Health check endpoint
```

## Quick Start

### Development

```bash
cd data_layer
cp .env.example .env
# Edit .env as needed

python manage.py migrate
python manage.py runserver 0.0.0.0:9010
```

### Production

```bash
# Set USE_NEON_POSTGRES=True in .env
# Configure NEON_* database URLs

gunicorn config.wsgi:application --bind 0.0.0.0:9010 --workers 4
```

## Using the Client SDK

Other services use the Data Layer Client to communicate:

```python
from data_layer.client import SyncDataLayerClient

# Initialize client
client = SyncDataLayerClient.from_env()

# Register a user
user = client.register_user({
    'email': 'user@example.com',
    'password': 'SecurePass123!',
    'first_name': 'John',
    'last_name': 'Doe',
    'role': 'talent',
    'terms_accepted': True,
    'privacy_accepted': True,
})

# Login
result = client.login('user@example.com', 'SecurePass123!')
access_token = result['tokens']['access']

# Get user data
user = client.get_user(user_id, auth_token=access_token)
```

## Database Modes

### Single Database (Development/Simple Hosting)

```env
USE_SINGLE_DATABASE=True
DATABASE_URL=sqlite:///data_layer.sqlite3
```

### Multi-Database (Production/Scale)

```env
USE_SINGLE_DATABASE=False
USE_NEON_POSTGRES=True
NEON_ACCOUNTS_URL=postgresql://...
NEON_PROFILES_URL=postgresql://...
# etc.
```

## Security

- JWT token authentication for user requests
- Service-to-service API key authentication
- Rate limiting (100/hour anon, 1000/hour auth)
- CORS protection
- Comprehensive audit logging
- POPIA/GDPR compliant

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATA_LAYER_ENV` | Environment (development/production) |
| `DATABASE_URL` | Default database connection |
| `USE_SINGLE_DATABASE` | Use one database for all |
| `USE_NEON_POSTGRES` | Use Neon PostgreSQL |
| `DATA_LAYER_API_KEY` | Service auth key |
| `JWT_SECRET_KEY` | JWT signing key |

---
**ForgeForth Africa** - Forging Africa's Future Through Talent
