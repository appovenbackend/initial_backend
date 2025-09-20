# Deployment Guide - Database Persistence Fix

## Problem
Users were not persisting in the database after redeployment because the application was falling back to SQLite instead of using PostgreSQL.

## Root Cause
- The application is designed to use PostgreSQL in production (Railway) via `DATABASE_URL` environment variable
- When `DATABASE_URL` is not set, it falls back to SQLite
- SQLite database files are gitignored, so they don't persist across deployments
- Railway provides `DATABASE_URL` automatically, but it may not be properly configured

## Solution
1. **Ensure PostgreSQL is attached** to your Railway service
2. **Verify DATABASE_URL** is set in Railway environment variables
3. **Check application logs** for database connection warnings

## Railway Deployment Steps

### 1. Attach PostgreSQL Database
- In Railway dashboard, go to your service
- Click "Add Plugin" → "PostgreSQL"
- This automatically creates a PostgreSQL database and sets `DATABASE_URL`

### 2. Verify Environment Variables
In Railway service settings, ensure these variables are set:
- `DATABASE_URL` (auto-provided by PostgreSQL plugin)
- `JWT_SECRET` (your JWT signing secret - **CRITICAL for user session persistence**)
- `GOOGLE_CLIENT_ID` (Google OAuth client ID)
- `GOOGLE_CLIENT_SECRET` (Google OAuth client secret)

**Important**: `JWT_SECRET` must remain consistent across deployments. If it changes, all user sessions will be invalidated.

### 3. Deploy and Check Logs
After deployment, check the application logs for:
- ✅ "Using PostgreSQL database for production persistence"
- ❌ "WARNING: Using SQLite database!" (this indicates DATABASE_URL is not set)

### 4. Health Check
Visit `https://your-app-url/health` to verify:
- `"database": {"type": "PostgreSQL", "postgresql_enabled": true}`
- `"users_count": <number>` shows existing users

## Local Development
- Uses SQLite (`data/app.db`)
- Data persists locally but is gitignored
- For production testing, set `DATABASE_URL` environment variable

## Troubleshooting

### If still using SQLite:
1. Check Railway variables tab - `DATABASE_URL` should be present
2. Redeploy the application
3. Check if PostgreSQL plugin is properly attached

### If PostgreSQL connection fails:
1. Verify database credentials in `DATABASE_URL`
2. Check Railway PostgreSQL plugin status
3. Ensure SSL mode is properly configured

### User Sessions Lost After Redeployment
If users lose authentication after redeployment:
1. Check that `JWT_SECRET` is set in Railway environment variables
2. Ensure `JWT_SECRET` remains the same across deployments
3. Look for "Using default JWT_SECRET!" warning in logs
4. If using default secret, set a custom `JWT_SECRET` in Railway variables

### Database Migration
If switching from SQLite to PostgreSQL, existing data will need to be migrated manually or users will need to re-register.

#### Adding New Columns to Existing Tables
When adding new columns to existing database tables (like organizer fields to events), run the migration script:

```bash
python migrate_db.py
```

This script will:
- Check if the new columns already exist
- Add missing columns with appropriate defaults
- Preserve existing data

**Important**: Always run migrations after deploying code that adds new database columns.
