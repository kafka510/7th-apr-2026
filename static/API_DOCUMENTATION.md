# API Server Documentation

## Complete Guide to Secure Data Access API

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Security Model](#security-model)
4. [Getting Started](#getting-started)
5. [Authentication](#authentication)
6. [API Endpoints](#api-endpoints)
7. [Schema Discovery](#schema-discovery)
8. [Data Access](#data-access)
9. [Rate Limiting](#rate-limiting)
10. [Error Handling](#error-handling)
11. [Code Examples](#code-examples)
12. [Best Practices](#best-practices)

---

## Overview

The API Server provides secure, read-only access to your database tables via RESTful API endpoints. It offers complete control over:

- **User Management**: Define API users and generate unique keys
- **Table Permissions**: Select which tables to expose
- **Column Restrictions**: Hide sensitive columns
- **Dynamic Schema**: Automatic reflection of database changes
- **Active Tokens**: Short-lived tokens for enhanced security
- **Rate Limiting**: Protect against abuse

**Important: This API is READ-ONLY. No write, update, or delete operations are supported.**

---

## Key Features

### 1. Secure API Key Management
- Industry-standard API key generation (SHA-256 hashing)
- Keys are never stored in plaintext
- Per-key usage tracking and statistics
- Expiration dates and revocation support

### 2. Table-Level Permissions
- Granular control over table access
- Enable/disable filtering and aggregations
- Set maximum records per request
- Automatic permission checking

### 3. Column-Level Restrictions
- Hide sensitive columns completely
- Mask columns (return as NULL)
- Automatic filtering in responses
- Protection of PII and confidential data

### 4. Active Token Authentication
- Short-lived tokens (default 60 minutes)
- Token-per-request or token reuse models
- Automatic expiration and cleanup
- Protection against replay attacks

### 5. Dynamic Schema Discovery
- List all accessible tables
- Get column information automatically
- Reflect database changes in real-time
- Type information and constraints

### 6. Rate Limiting
- Per-minute, per-hour, and per-day limits
- Configurable per API user
- Automatic enforcement
- Retry-After headers

---

## Security Model

### Multi-Layer Security

```
┌─────────────────────────────────────┐
│  1. API Key Verification             │
│  - SHA-256 hash validation           │
│  - Expiration check                  │
│  - Status verification               │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│  2. IP Restriction (Optional)        │
│  - Whitelist enforcement             │
│  - Geographic restrictions           │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│  3. Active Token Verification        │
│  - Token lifetime check              │
│  - Usage count validation            │
│  - Token-key pairing                 │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│  4. Rate Limit Enforcement           │
│  - Minute/hour/day tracking          │
│  - Automatic throttling              │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│  5. Table Permission Check           │
│  - Access verification               │
│  - Operation validation              │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│  6. Column Filtering                 │
│  - Sensitive data removal            │
│  - Masking application               │
└─────────────────────────────────────┘
```

---

## Getting Started

### Step 1: Access the API Dashboard

Navigate to: `https://your-domain.com/api/dashboard/`

Log in with your Django account credentials.

### Step 2: Generate an API Key

1. Click **"Generate New Key"**
2. Enter a descriptive name (e.g., "Production App")
3. Optionally set an expiration date
4. Click **"Generate"**
5. **IMPORTANT**: Copy and save the API key immediately. It will never be shown again.

### Step 3: Contact Administrator for Permissions

Your administrator needs to grant you access to specific tables. Contact them with:
- Your username
- The tables you need access to
- Any column restrictions needed

### Step 4: Test Your API Key

```bash
curl -X GET "https://your-domain.com/api/v1/schema/tables" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Authentication

### Method 1: Authorization Header (Recommended)

```http
GET /api/v1/schema/tables HTTP/1.1
Host: your-domain.com
Authorization: Bearer YOUR_API_KEY
```

### Method 2: X-API-Key Header

```http
GET /api/v1/schema/tables HTTP/1.1
Host: your-domain.com
X-API-Key: YOUR_API_KEY
```

### Method 3: Query Parameter

```http
GET /api/v1/schema/tables?api_key=YOUR_API_KEY HTTP/1.1
Host: your-domain.com
```

**Note**: Method 1 (Authorization header) is recommended for security.

---

## Active Token Authentication

For enhanced security, some endpoints require an **active token** in addition to the API key.

### Requesting a Token

**Endpoint**: `POST /api/v1/auth/token`

**Request Body**:
```json
{
  "api_key": "YOUR_API_KEY",
  "lifetime_minutes": 60,
  "max_uses": 100
}
```

**Response**:
```json
{
  "success": true,
  "token": "ACTIVE_TOKEN_STRING",
  "expires_at": "2025-10-20T12:00:00Z",
  "lifetime_minutes": 60,
  "max_uses": 100,
  "created_at": "2025-10-20T11:00:00Z"
}
```

### Using the Token

Include the token in the `X-Active-Token` header:

```http
GET /api/v1/data/asset_list HTTP/1.1
Host: your-domain.com
Authorization: Bearer YOUR_API_KEY
X-Active-Token: ACTIVE_TOKEN_STRING
```

---

## API Endpoints

### Base URL

```
Production: https://your-domain.com/api/
Development: http://localhost:8000/api/
```

### Endpoint Overview

| Endpoint | Method | Auth Required | Token Required | Description |
|----------|--------|---------------|----------------|-------------|
| `/v1/auth/token` | POST | API Key | No | Generate active token |
| `/v1/schema/tables` | GET | API Key | No | List accessible tables |
| `/v1/schema/tables/{table}` | GET | API Key | No | Get table schema |
| `/v1/data/{table}` | GET | API Key | Yes | Get table data |
| `/v1/data/{table}/aggregate` | GET | API Key | Yes | Aggregate data |

---

## Schema Discovery

### List All Accessible Tables

**Endpoint**: `GET /api/v1/schema/tables`

**Response**:
```json
{
  "success": true,
  "tables": [
    {
      "name": "asset_list",
      "permissions": {
        "can_read": true,
        "can_filter": true,
        "can_aggregate": true,
        "max_records_per_request": 1000
      }
    },
    {
      "name": "device_list",
      "permissions": {
        "can_read": true,
        "can_filter": false,
        "can_aggregate": false,
        "max_records_per_request": 500
      }
    }
  ],
  "total_count": 2
}
```

### Get Table Schema

**Endpoint**: `GET /api/v1/schema/tables/{table_name}`

**Example**: `GET /api/v1/schema/tables/asset_list`

**Response**:
```json
{
  "success": true,
  "table_name": "asset_list",
  "columns": [
    {
      "name": "asset_code",
      "type": "CharField",
      "max_length": 255,
      "nullable": false,
      "primary_key": true,
      "is_restricted": false,
      "description": "Asset code"
    },
    {
      "name": "asset_name",
      "type": "CharField",
      "max_length": 255,
      "nullable": false,
      "primary_key": false,
      "is_restricted": false,
      "description": "Asset name"
    },
    {
      "name": "api_key",
      "type": "TextField",
      "nullable": true,
      "primary_key": false,
      "is_restricted": true
    }
  ],
  "total_columns": 20,
  "permissions": {
    "can_read": true,
    "can_filter": true,
    "can_aggregate": true,
    "max_records_per_request": 1000
  }
}
```

---

## Data Access

### Get Table Data

**Endpoint**: `GET /api/v1/data/{table_name}`

**Query Parameters**:
- `page` (integer): Page number (default: 1)
- `page_size` (integer): Records per page (default: 100)
- `filter` (JSON): Filter conditions
- `fields` (string): Comma-separated field list
- `order_by` (string): Field to sort by (prefix with `-` for descending)

**Example 1: Basic Query**
```http
GET /api/v1/data/asset_list?page=1&page_size=10
```

**Example 2: With Filters**
```http
GET /api/v1/data/asset_list?filter={"country":"South Korea"}&page=1&page_size=50
```

**Example 3: Select Specific Fields**
```http
GET /api/v1/data/asset_list?fields=asset_code,asset_name,country&page_size=100
```

**Example 4: With Sorting**
```http
GET /api/v1/data/asset_list?order_by=-created_at&page_size=20
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "asset_code": "KR_BW_01",
      "asset_name": "Boryeong Wind Farm",
      "country": "South Korea",
      "capacity": 100.5,
      "latitude": 36.3274,
      "longitude": 126.5572
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_records": 150,
    "total_pages": 15,
    "has_next": true,
    "has_previous": false
  }
}
```

### Aggregate Data

**Endpoint**: `GET /api/v1/data/{table_name}/aggregate`

**Query Parameters**:
- `operation` (string): `count`, `sum`, `avg`, `min`, `max`
- `field` (string): Field to aggregate (not needed for count)
- `filter` (JSON): Filter conditions

**Example 1: Count Records**
```http
GET /api/v1/data/asset_list/aggregate?operation=count
```

**Example 2: Sum Values**
```http
GET /api/v1/data/asset_list/aggregate?operation=sum&field=capacity
```

**Example 3: Average with Filter**
```http
GET /api/v1/data/asset_list/aggregate?operation=avg&field=capacity&filter={"country":"Japan"}
```

**Response**:
```json
{
  "success": true,
  "result": 2543.75,
  "operation": "avg",
  "field": "capacity"
}
```

---

## Rate Limiting

### Rate Limit Headers

Every response includes rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit-Minute: 60
X-RateLimit-Limit-Hour: 1000
X-RateLimit-Limit-Day: 10000
```

### Rate Limit Exceeded Response

When you exceed the rate limit:

```json
{
  "error": "Rate limit exceeded",
  "message": "You have exceeded the hourly rate limit. Please try again later.",
  "limit_type": "hour",
  "retry_after_seconds": 1847,
  "code": "RATE_LIMIT_EXCEEDED"
}
```

The response will also include:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 1847
```

---

## Error Handling

### Standard Error Response

```json
{
  "error": "Error Title",
  "message": "Detailed error message",
  "code": "ERROR_CODE"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_REQUIRED` | 401 | API key not provided |
| `INVALID_API_KEY` | 401 | Invalid or expired API key |
| `TOKEN_REQUIRED` | 401 | Active token not provided |
| `INVALID_TOKEN` | 401 | Invalid or expired token |
| `IP_NOT_ALLOWED` | 403 | IP address not whitelisted |
| `TABLE_ACCESS_DENIED` | 403 | No permission for table |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `TABLE_NOT_FOUND` | 404 | Table doesn't exist or no access |
| `INVALID_FILTER` | 400 | Malformed filter JSON |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Code Examples

### Python Example

```python
import requests
import json

# Configuration
API_BASE_URL = "https://your-domain.com/api"
API_KEY = "your-api-key-here"

class APIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.active_token = None
        self.headers = {
            "Authorization": f"Bearer {api_key}"
        }
    
    def get_token(self, lifetime_minutes=60):
        """Get an active token"""
        response = requests.post(
            f"{API_BASE_URL}/v1/auth/token",
            json={
                "api_key": self.api_key,
                "lifetime_minutes": lifetime_minutes
            }
        )
        data = response.json()
        if data.get("success"):
            self.active_token = data["token"]
            return self.active_token
        else:
            raise Exception(f"Failed to get token: {data}")
    
    def list_tables(self):
        """List all accessible tables"""
        response = requests.get(
            f"{API_BASE_URL}/v1/schema/tables",
            headers=self.headers
        )
        return response.json()
    
    def get_table_schema(self, table_name):
        """Get schema for a specific table"""
        response = requests.get(
            f"{API_BASE_URL}/v1/schema/tables/{table_name}",
            headers=self.headers
        )
        return response.json()
    
    def get_data(self, table_name, filters=None, page=1, page_size=100):
        """Get data from a table"""
        if not self.active_token:
            self.get_token()
        
        headers = self.headers.copy()
        headers["X-Active-Token"] = self.active_token
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if filters:
            params["filter"] = json.dumps(filters)
        
        response = requests.get(
            f"{API_BASE_URL}/v1/data/{table_name}",
            headers=headers,
            params=params
        )
        return response.json()
    
    def aggregate(self, table_name, operation, field=None, filters=None):
        """Perform aggregation on a table"""
        if not self.active_token:
            self.get_token()
        
        headers = self.headers.copy()
        headers["X-Active-Token"] = self.active_token
        
        params = {
            "operation": operation
        }
        
        if field:
            params["field"] = field
        
        if filters:
            params["filter"] = json.dumps(filters)
        
        response = requests.get(
            f"{API_BASE_URL}/v1/data/{table_name}/aggregate",
            headers=headers,
            params=params
        )
        return response.json()

# Usage Example
if __name__ == "__main__":
    client = APIClient(API_KEY)
    
    # List all tables
    tables = client.list_tables()
    print("Available tables:", tables)
    
    # Get schema for asset_list
    schema = client.get_table_schema("asset_list")
    print("Schema:", schema)
    
    # Get data from asset_list
    data = client.get_data("asset_list", 
                          filters={"country": "South Korea"},
                          page_size=10)
    print("Data:", data)
    
    # Count total assets
    count = client.aggregate("asset_list", "count")
    print("Total assets:", count)
    
    # Sum of all capacities
    total_capacity = client.aggregate("asset_list", "sum", field="capacity")
    print("Total capacity:", total_capacity)
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const API_BASE_URL = 'https://your-domain.com/api';
const API_KEY = 'your-api-key-here';

class APIClient {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.activeToken = null;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`
        };
    }

    async getToken(lifetimeMinutes = 60) {
        const response = await axios.post(`${API_BASE_URL}/v1/auth/token`, {
            api_key: this.apiKey,
            lifetime_minutes: lifetimeMinutes
        });
        
        if (response.data.success) {
            this.activeToken = response.data.token;
            return this.activeToken;
        } else {
            throw new Error(`Failed to get token: ${JSON.stringify(response.data)}`);
        }
    }

    async listTables() {
        const response = await axios.get(`${API_BASE_URL}/v1/schema/tables`, {
            headers: this.headers
        });
        return response.data;
    }

    async getTableSchema(tableName) {
        const response = await axios.get(
            `${API_BASE_URL}/v1/schema/tables/${tableName}`,
            { headers: this.headers }
        );
        return response.data;
    }

    async getData(tableName, options = {}) {
        if (!this.activeToken) {
            await this.getToken();
        }

        const headers = {
            ...this.headers,
            'X-Active-Token': this.activeToken
        };

        const params = {
            page: options.page || 1,
            page_size: options.pageSize || 100
        };

        if (options.filters) {
            params.filter = JSON.stringify(options.filters);
        }

        if (options.fields) {
            params.fields = options.fields.join(',');
        }

        if (options.orderBy) {
            params.order_by = options.orderBy;
        }

        const response = await axios.get(
            `${API_BASE_URL}/v1/data/${tableName}`,
            { headers, params }
        );
        return response.data;
    }

    async aggregate(tableName, operation, options = {}) {
        if (!this.activeToken) {
            await this.getToken();
        }

        const headers = {
            ...this.headers,
            'X-Active-Token': this.activeToken
        };

        const params = { operation };

        if (options.field) {
            params.field = options.field;
        }

        if (options.filters) {
            params.filter = JSON.stringify(options.filters);
        }

        const response = await axios.get(
            `${API_BASE_URL}/v1/data/${tableName}/aggregate`,
            { headers, params }
        );
        return response.data;
    }
}

// Usage Example
(async () => {
    const client = new APIClient(API_KEY);

    try {
        // List all tables
        const tables = await client.listTables();
        console.log('Available tables:', tables);

        // Get schema
        const schema = await client.getTableSchema('asset_list');
        console.log('Schema:', schema);

        // Get data
        const data = await client.getData('asset_list', {
            filters: { country: 'South Korea' },
            pageSize: 10,
            fields: ['asset_code', 'asset_name', 'capacity']
        });
        console.log('Data:', data);

        // Aggregate
        const count = await client.aggregate('asset_list', 'count');
        console.log('Total assets:', count);

    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
})();
```

### cURL Examples

```bash
# 1. Generate Active Token
curl -X POST "https://your-domain.com/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"YOUR_API_KEY","lifetime_minutes":60}'

# 2. List Tables
curl -X GET "https://your-domain.com/api/v1/schema/tables" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 3. Get Table Schema
curl -X GET "https://your-domain.com/api/v1/schema/tables/asset_list" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 4. Get Data
curl -X GET "https://your-domain.com/api/v1/data/asset_list?page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-Active-Token: YOUR_ACTIVE_TOKEN"

# 5. Get Data with Filters
curl -X GET 'https://your-domain.com/api/v1/data/asset_list?filter={"country":"South Korea"}' \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-Active-Token: YOUR_ACTIVE_TOKEN"

# 6. Aggregate
curl -X GET "https://your-domain.com/api/v1/data/asset_list/aggregate?operation=count" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "X-Active-Token: YOUR_ACTIVE_TOKEN"
```

---

## Best Practices

### 1. Security

- **Never expose API keys** in client-side code (HTML, JavaScript)
- **Use HTTPS** in production to encrypt API keys in transit
- **Rotate keys** periodically (every 90 days recommended)
- **Use active tokens** for enhanced security
- **Monitor usage** through the admin dashboard
- **Set expiration dates** on API keys when possible

### 2. Performance

- **Use pagination** for large datasets
- **Request only needed fields** with the `fields` parameter
- **Cache responses** when data doesn't change frequently
- **Use aggregations** instead of fetching full datasets
- **Respect rate limits** and implement exponential backoff

### 3. Error Handling

- **Check HTTP status codes** before processing responses
- **Implement retry logic** with exponential backoff
- **Log errors** for debugging
- **Handle rate limit errors** by respecting `Retry-After` header
- **Validate responses** before using data

### 4. Development

- **Test in development** before production deployment
- **Use descriptive key names** for easier management
- **Document API usage** in your application
- **Monitor API logs** for suspicious activity
- **Keep API documentation** updated

---

## Administrator Guide

### Setting Up API Access for Users

#### 1. Create API User

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from api.models import APIUser

user = User.objects.get(username='john.doe')
api_user = APIUser.objects.create(
    user=user,
    name="John Doe's API Access",
    description="Production data access",
    status='active',
    rate_limit_per_minute=60,
    rate_limit_per_hour=1000,
    rate_limit_per_day=10000
)
```

#### 2. Grant Table Permissions

```python
from api.models import TablePermission

# Grant access to asset_list table
TablePermission.objects.create(
    api_user=api_user,
    table_name='asset_list',
    can_read=True,
    can_filter=True,
    can_aggregate=True,
    max_records_per_request=1000
)

# Grant access to device_list table
TablePermission.objects.create(
    api_user=api_user,
    table_name='device_list',
    can_read=True,
    can_filter=True,
    can_aggregate=False,
    max_records_per_request=500
)
```

#### 3. Add Column Restrictions

```python
from api.models import ColumnRestriction

# Hide sensitive columns
permission = TablePermission.objects.get(
    api_user=api_user,
    table_name='asset_list'
)

# Hide api_key column
ColumnRestriction.objects.create(
    table_permission=permission,
    column_name='api_key',
    restriction_type='hidden'
)

# Hide contact information
ColumnRestriction.objects.create(
    table_permission=permission,
    column_name='contact_method',
    restriction_type='hidden'
)
```

#### 4. Set IP Restrictions (Optional)

```python
api_user.allowed_ips = '203.0.113.0, 198.51.100.0'
api_user.save()
```

---

## Support

For issues or questions:
- Contact your system administrator
- Check the admin logs at `/admin/api/`
- Review API request logs for debugging

---

## Changelog

### Version 1.0.0 (2025-10-20)
- Initial release
- API key authentication
- Active token support
- Table and column permissions
- Rate limiting
- Schema discovery
- Read-only data access
- Aggregation support

---

**Last Updated**: October 20, 2025  
**API Version**: 1.0.0  
**Author**: Peak Energy GK

