# 🚀 Railway PostgreSQL Deployment Guide

## Overview
This application is designed to automatically switch between SQLite (local development) and PostgreSQL (production deployment) based on environment variables.

## Railway Deployment Steps

### 1. Deploy to Railway
1. Connect your GitHub repository to Railway
2. Railway will automatically detect this is a Python application
3. The build process will install all dependencies from `requirements.txt`

### 2. Add PostgreSQL Database
1. In your Railway project, go to the **Database** tab
2. Click **New** → **Add PostgreSQL**
3. Railway will automatically provide a `DATABASE_URL` environment variable

### 3. Set Environment Variables
Add these environment variables in your Railway project settings:

#### Required Variables:
```bash
DATABASE_URL=postgresql://[auto-provided-by-railway]
JWT_SECRET=your-super-secret-jwt-key-here
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
```

#### Optional Variables (with defaults):
```bash
REDIS_URL=redis://host:port
REDIS_PASSWORD=your-redis-password
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=300
DB_POOL_TIMEOUT=30
DB_POOL_PRE_PING=true
```

### 4. Redeploy
After setting the environment variables, trigger a redeploy:
- Go to the **Deployments** tab
- Click **Deploy latest commit**

## How Auto-Switching Works

### Local Development (No DATABASE_URL)
```
⚠️  WARNING: Using SQLite database! This will NOT persist data across deployments.
=== DATABASE CONFIGURATION ===
DATABASE_URL present: False
USE_POSTGRESQL: False
Using SQLite: data/app.db
===============================
```

### Production Deployment (With DATABASE_URL)
```
✅ Using PostgreSQL database for production persistence.
=== DATABASE CONFIGURATION ===
DATABASE_URL present: True
USE_POSTGRESQL: True
DATABASE_URL starts with: postgresql://...
===============================
```

## Database Schema
The application automatically creates all necessary tables:
- `users` - User accounts and profiles
- `events` - Event information and organizer details
- `tickets` - Ticket management and validation
- `received_qr_tokens` - QR code token storage

## Production Features
- ✅ **SSL Connections**: Automatically configured for Railway PostgreSQL
- ✅ **Connection Pooling**: Optimized for production performance
- ✅ **Error Handling**: Robust database connection retry logic
- ✅ **Migration Support**: Database schema updates handled automatically
- ✅ **Monitoring**: Health check endpoints for production monitoring

## Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | None |
| `JWT_SECRET` | JWT token signing secret | Yes | `supersecretkey123` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Yes | None |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Yes | None |
| `REDIS_URL` | Redis connection URL | No | `localhost:6379` |
| `REDIS_PASSWORD` | Redis password | No | None |
| `DB_POOL_SIZE` | Database connection pool size | No | `20` |
| `DB_MAX_OVERFLOW` | Max overflow connections | No | `20` |
| `DB_POOL_RECYCLE` | Connection recycle time (seconds) | No | `300` |
| `DB_POOL_TIMEOUT` | Connection timeout (seconds) | No | `30` |
| `DB_POOL_PRE_PING` | Pre-ping connections | No | `true` |
| `DB_CONNECT_TIMEOUT` | Connection timeout (seconds) | No | `10` |
| `DB_STATEMENT_TIMEOUT_MS` | Query timeout (milliseconds) | No | `30000` |
| `USE_PGBOUNCER` | Use PgBouncer (disables SQLAlchemy pooling) | No | `false` |

## Health Monitoring
Once deployed, monitor your application using:
- `GET /health` - Comprehensive system health check
- `GET /cache-stats` - Cache performance metrics
- Railway's built-in monitoring dashboard

## Troubleshooting
1. **Database Connection Issues**: Check that `DATABASE_URL` is correctly set
2. **SSL Errors**: The app automatically adds `?sslmode=require` for Railway
3. **Performance Issues**: Adjust connection pool settings via environment variables
4. **JWT Session Loss**: Ensure `JWT_SECRET` is set to a persistent value

## Security Notes
- Never commit `JWT_SECRET` or OAuth credentials to version control
- Use Railway's environment variable encryption for sensitive data
- Monitor database connections in production
- Enable Railway's automatic HTTPS for secure connections

---
**Ready for Production!** 🚀 Your application will automatically use PostgreSQL when deployed to Railway with the proper environment variables configured.
