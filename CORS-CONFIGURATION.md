# CORS Configuration

This document explains the CORS (Cross-Origin Resource Sharing) configuration for the Patient API.

## Overview

CORS has been configured to allow requests from specific origins while maintaining security. The configuration supports both development and production environments.

## Configuration Details

### Development Environment

**Allowed Origins:**
- `http://localhost:4200` (Angular default port)
- `http://localhost:3000` (React default port)
- `http://127.0.0.1:4200` (Alternative localhost)
- `http://127.0.0.1:3000` (Alternative localhost)

**Allowed Methods:**
- `GET`
- `POST`
- `PUT`
- `DELETE`
- `OPTIONS`

**Allowed Headers:**
- `Content-Type`
- `Authorization`

**Credentials:** Supported (`supports_credentials=True`)

### Production Environment

**Allowed Origins:** Configure via `CORS_ORIGINS` environment variable
- Example: `https://yourdomain.com,https://www.yourdomain.com`

## Environment Variables

### Development (.env file)
```bash
CORS_ORIGINS=http://localhost:4200,http://localhost:3000,http://127.0.0.1:4200,http://127.0.0.1:3000
```

### Production
```bash
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## Docker Configuration

### Development (docker-compose.dev.yml)
```yaml
environment:
  - CORS_ORIGINS=http://localhost:4200,http://localhost:3000,http://127.0.0.1:4200,http://127.0.0.1:3000
```

### Production (docker-compose.yml)
```yaml
environment:
  - CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## Testing CORS

### Test Preflight Request
```bash
curl -s -I -H "Origin: http://localhost:4200" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  -X OPTIONS \
  http://localhost:5001/api/patients/
```

**Expected Response Headers:**
```
Access-Control-Allow-Origin: http://localhost:4200
Access-Control-Allow-Credentials: true
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Allow-Methods: DELETE, GET, OPTIONS, POST, PUT
```

### Test Actual Request
```bash
curl -s -H "Origin: http://localhost:4200" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:5001/api/patients/
```

## Angular Integration

Your Angular application should now be able to make requests to the API without CORS issues. The service configuration in the Angular examples already includes the proper headers:

```typescript
private getHeaders(): HttpHeaders {
  const token = this.tokenSubject.value;
  return new HttpHeaders({
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` })
  });
}
```

## Security Considerations

1. **Specific Origins**: Only allow specific domains, not wildcards
2. **HTTPS in Production**: Always use HTTPS for production origins
3. **Credentials**: Only enable when necessary (currently enabled for JWT tokens)
4. **Headers**: Only allow necessary headers

## Troubleshooting

### Common CORS Errors

1. **"Access to fetch at '...' from origin '...' has been blocked by CORS policy"**
   - Check if your origin is in the `CORS_ORIGINS` list
   - Verify the environment variable is set correctly

2. **"Response to preflight request doesn't pass access control check"**
   - Ensure the preflight request returns proper CORS headers
   - Check that the requested method and headers are allowed

3. **"Credentials flag is true, but the 'Access-Control-Allow-Credentials' header is not set"**
   - The configuration includes `supports_credentials=True`
   - This should be working correctly

### Debug Steps

1. Check the browser's Network tab for CORS-related errors
2. Verify the preflight OPTIONS request returns 200 status
3. Check the response headers for proper CORS headers
4. Ensure your frontend origin matches the configured origins

## Updating CORS Origins

To add new origins:

1. **Development**: Update the `CORS_ORIGINS` environment variable
2. **Production**: Update the environment variable in your deployment
3. **Docker**: Update the docker-compose files
4. **Restart**: Restart the application to apply changes

Example:
```bash
# Add a new development origin
CORS_ORIGINS=http://localhost:4200,http://localhost:3000,http://localhost:8080
```

## Code Implementation

The CORS configuration is implemented in `app/__init__.py`:

```python
# Configure CORS
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:4200,http://localhost:3000,http://127.0.0.1:4200,http://127.0.0.1:3000').split(',')
CORS(app, 
     origins=cors_origins,
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True)
```

This configuration ensures secure and flexible CORS handling for your Patient API.
