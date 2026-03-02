# CHRONOS Deployment Guide

## Overview

CHRONOS is deployed as a containerized application with PostgreSQL as the database backend. This guide covers local development, Docker deployment, and production deployment on Render.com.

### Tech Stack
- **Frontend**: React 18.3 + Streamlit
- **Backend**: Python 3.11 + FastAPI
- **Database**: PostgreSQL 15+ (from SQLite)
- **Container**: Docker + Docker Compose
- **Deployment**: Render.com

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ (optional, can use Docker)
- Docker & Docker Compose (recommended)
- Git

### Option A: Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/chronos.git
cd chronos

# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d

# Logs
docker-compose logs -f app

# Stop services
docker-compose down
```

**Access Points:**
- Streamlit App: http://localhost:8501
- PostgreSQL: localhost:5432
- PgAdmin: http://localhost:5050

### Option B: Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your PostgreSQL connection string

# Initialize database
python -c "from database.postgres_schema import init_database; init_database()"

# Run application
cd Chronos
streamlit run app.py
```

---

## Database Migration (SQLite → PostgreSQL)

### Automated Migration Script

The project includes migration tools to convert existing SQLite data:

```bash
# From project root
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite_path ./Chronos/chronos.db \
  --postgres_url postgresql://user:password@localhost:5432/chronos_db
```

### Manual Migration Steps

1. **Export SQLite data:**
```bash
sqlite3 Chronos/chronos.db ".dump" > backup.sql
```

2. **Transform SQL (SQLite → PostgreSQL):**
   - Replace `AUTOINCREMENT` with `SERIAL`
   - Remove SQLite pragmas (`PRAGMA`, `journal_mode`)
   - Use PostgreSQL UUID functions

3. **Import to PostgreSQL:**
```bash
psql -U chronos -d chronos_db -f backup.sql
```

---

## Docker Build & Run

### Build Locally

```bash
# Build image
docker build -t chronos:latest .

# Run container
docker run -d \
  --name chronos_app \
  -p 8501:8501 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e GOOGLE_API_KEY=your_api_key \
  chronos:latest

# View logs
docker logs -f chronos_app
```

### Multi-stage Build Benefits

The Dockerfile uses a multi-stage build to:
- Reduce final image size (builder stage discarded)
- Include only production dependencies
- Run as non-root user (security)
- Include health checks

---

## Production Deployment on Render.com

### Step 1: Prepare Repository

```bash
# Ensure all files are committed
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### Step 2: Connect Render.com

1. Go to https://dashboard.render.com
2. Click "New +"
3. Select "Web Service"
4. Connect your GitHub repository
5. Fill in details:
   - **Name**: `chronos-app`
   - **Repository**: Your repo
   - **Branch**: `main`
   - **Root Directory**: `.`
   - **Environment**: `Docker`
   - **Plan**: `Standard` (0.05 USD/hour)

### Step 3: Configure Environment Variables

In Render Dashboard, add:

```
DATABASE_URL=postgresql://user:pass@host:5432/db
GOOGLE_API_KEY=your_api_key
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_PORT=8501
PYTHONUNBUFFERED=1
```

**For DATABASE_URL**, use Render's managed PostgreSQL:
1. In Render Dashboard, create a "PostgreSQL Database"
2. Copy the connection string to `DATABASE_URL` env var

### Step 4: Deploy

1. Push code to `main` branch
2. Render automatically builds and deploys
3. Monitor deployment: Dashboard → Web Service → Logs

### Step 5: Database Initialization

After first deployment, initialize the database:

```bash
# Connect to Render service shell
render run --service=chronos-app --command="python -c 'from database.postgres_schema import init_database; init_database()'"
```

---

## Configuration

### Environment Variables

| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `GOOGLE_API_KEY` | Google Generative AI API key | Yes | - |
| `STREAMLIT_SERVER_PORT` | Port for Streamlit | No | 8501 |
| `STREAMLIT_SERVER_HEADLESS` | Run without browser | No | true |
| `DEBUG` | Debug mode | No | false |

### Database Connection Strings

**Local PostgreSQL:**
```
postgresql://chronos:password@localhost:5432/chronos_db
```

**Render Managed:**
```
postgresql://user:password@pg-xxxxx.render-db.com:5432/dbname
```

**Heroku PostgreSQL:**
```
postgresql://user:password@ec2-xxxxx.compute-1.amazonaws.com:5432/dbname
```

---

## Health Checks & Monitoring

### Docker Health Check

The Dockerfile includes an HTTP health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501/_stcore/health')"
```

### Render Monitoring

1. **Health Check Endpoint**: `/_stcore/health`
2. **Response Time**: < 10 seconds
3. **Failure Threshold**: 3 consecutive failures = restart

### View Logs

```bash
# Docker
docker logs chronos_app

# Render CLI
render logs --service=chronos-app

# Render Dashboard
Settings → Logs
```

---

## Scaling & Performance

### Auto-scaling on Render

Configure in `render.yaml`:

```yaml
scaling:
  minInstances: 1
  maxInstances: 3
  targetCPUUtilizationPercentage: 70
```

This scales horizontally if CPU > 70%.

### Database Connection Pooling

PostgreSQL uses `NullPool` for cloud deployments (Render, Heroku) to prevent connection exhaustion:

```python
if "render.com" in DATABASE_URL or "heroku" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, poolclass=NullPool)
```

### Optimization Tips

1. **Cache AI responses** (24-hour TTL)
2. **Use database indexes** on frequently queried columns
3. **Limit concurrent connections** in Streamlit config
4. **Compress images** before upload

---

## Troubleshooting

### Docker Issues

```bash
# Container won't start
docker logs chronos_app

# Permission denied
sudo docker-compose up

# Port already in use
docker ps  # Find conflicting container
docker stop <container_id>
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql $DATABASE_URL -c "SELECT 1"

# Check if database exists
psql $DATABASE_URL -c "\l"

# Initialize tables if missing
python -c "from database.postgres_schema import init_database; init_database()"
```

### Render Deployment Issues

```bash
# Check health status
curl https://chronos-app.render.com/_stcore/health

# View deployment logs
render logs --service=chronos-app --tail=100

# Re-deploy manually
git push origin main  # Triggers auto-deploy
# OR manually in Render Dashboard
```

### Out of Memory

If Docker/Render runs out of memory:

1. Increase instance size on Render
2. Reduce `--memory` limit in docker-compose
3. Check for memory leaks in Python code

```bash
# Monitor container memory
docker stats chronos_app
```

---

## Security Checklist

- [ ] `.env` file NOT committed to git (use `.gitignore`)
- [ ] `SECRET_KEY` generated and unique
- [ ] Database user has minimal required permissions
- [ ] HTTPS enforced on Render
- [ ] API keys rotated regularly
- [ ] Docker image runs as non-root user
- [ ] Health check endpoint protected (optional)
- [ ] Security headers configured in render.yaml

---

## Backup & Recovery

### Automated Backups

Render PostgreSQL includes automated backups:
- **Frequency**: Daily
- **Retention**: 7 days
- **Access**: Render Dashboard → Database → Backups

### Manual Backup

```bash
# Backup PostgreSQL database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore from backup
psql $DATABASE_URL < backup_20240228.sql
```

---

## Continuous Integration/Deployment (CI/CD)

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Render

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Render
        run: |
          curl -X POST https://api.render.com/deploy/srv-${{ secrets.RENDER_SERVICE_ID }}?key=${{ secrets.RENDER_API_KEY }}
```

---

## Support & Resources

- **Render Documentation**: https://render.com/docs
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Streamlit Deployment**: https://docs.streamlit.io/deploy
- **Docker Documentation**: https://docs.docker.com
- **Project Issues**: GitHub Issues in repository

---

## Summary Checklist

**Local Development:**
- [ ] Docker Compose installed
- [ ] `.env` configured with database credentials
- [ ] `docker-compose up -d` running successfully
- [ ] Access http://localhost:8501

**Production Deployment:**
- [ ] Render account created
- [ ] GitHub repository connected
- [ ] PostgreSQL database provisioned on Render
- [ ] Environment variables configured
- [ ] Health checks passing
- [ ] Data migrated from SQLite

**Monitoring:**
- [ ] Logs checked for errors
- [ ] Database backups verified
- [ ] Auto-scaling configured
- [ ] Security headers enabled

---

**Last Updated**: February 28, 2026
**Version**: 3.1.0
**Maintained By**: CHRONOS Development Team
