# CHRONOS Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Docker & Docker Compose installed
- Git
- Google Generative AI API key

### Step 1: Clone & Setup

```bash
git clone https://github.com/yourusername/chronos.git
cd chronos

# Copy environment template
cp .env.example .env

# Edit .env and add your Google API key
nano .env  # or use your favorite editor
```

### Step 2: Start Services

```bash
# Start PostgreSQL + Streamlit app + PgAdmin
docker-compose up -d

# Watch logs
docker-compose logs -f app
```

### Step 3: Access Application

- **Streamlit App**: http://localhost:8501
- **PgAdmin** (database admin): http://localhost:5050
  - Email: admin@example.com (from .env)
  - Password: admin_password (from .env)

### Step 4: Initialize Database

The database initializes automatically on first run. To verify:

```bash
docker-compose exec app python -c "from database.postgres_schema import init_database; init_database()"
```

---

## 📊 Common Commands

### Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f app

# Rebuild images
docker-compose up -d --build

# Execute command in container
docker-compose exec app python -c "print('Hello')"

# Clean up (removes volumes)
docker-compose down -v
```

### Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U chronos -d chronos_db

# List tables
\dt

# Quit
\q

# Backup database
docker-compose exec postgres pg_dump -U chronos chronos_db > backup.sql

# Restore from backup
cat backup.sql | docker-compose exec -T postgres psql -U chronos -d chronos_db
```

---

## 🔧 Customization

### Add Environment Variables

Edit `.env`:

```bash
# Database
DATABASE_URL=postgresql://chronos:password@postgres:5432/chronos_db
DB_USER=chronos
DB_PASSWORD=your_password

# Google API
GOOGLE_API_KEY=your_api_key

# Streamlit
STREAMLIT_SERVER_PORT=8501

# Debug
DEBUG=true
LOG_LEVEL=DEBUG
```

Restart services for changes to take effect:

```bash
docker-compose restart app
```

### Modify Python Code

Edit files in `Chronos/` directory. Changes are auto-reloaded (Streamlit hot-reload):

```
Chronos/
├── app.py                 # Main Streamlit app
├── database/
│   ├── postgres_schema.py # ORM models
│   └── queries.py         # Database queries
├── logic/
│   ├── context.py        # Context detection
│   ├── engine.py         # Decision engine
│   └── __init__.py
├── services/
│   ├── vision.py         # Google AI integration
│   └── __init__.py
└── requirements.txt      # Python dependencies
```

### Update Dependencies

```bash
# Edit requirements.txt
nano requirements.txt

# Rebuild Docker image
docker-compose up -d --build app
```

---

## 🐛 Debugging

### View Application Logs

```bash
# Real-time logs
docker-compose logs -f app

# Last 100 lines
docker-compose logs --tail=100 app

# Specific service
docker-compose logs app
docker-compose logs postgres
```

### Connect to Database Directly

```bash
# Via docker-compose
docker-compose exec postgres psql -U chronos -d chronos_db

# View images table
SELECT id, title, primary_mood FROM images;

# View decision logs
SELECT * FROM context_logs ORDER BY timestamp DESC LIMIT 5;
```

### Python REPL in Container

```bash
docker-compose exec app python

# Inside Python:
>>> from database.postgres_schema import SessionLocal, Image
>>> db = SessionLocal()
>>> images = db.query(Image).all()
>>> print(f"Total images: {len(images)}")
```

---

## 📦 Build for Deployment

### Local Docker Build

```bash
# Build image
docker build -t chronos:latest .

# Run standalone
docker run -d \
  -p 8501:8501 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e GOOGLE_API_KEY=your_key \
  chronos:latest

# View logs
docker logs -f <container_id>
```

### Push to Container Registry (Docker Hub)

```bash
# Login to Docker Hub
docker login

# Tag image
docker tag chronos:latest your_username/chronos:latest

# Push
docker push your_username/chronos:latest
```

---

## 🔐 Security Notes

⚠️ **Never commit `.env` file!**

```bash
# Verify .env is ignored
git status | grep .env  # Should be empty
```

✅ **Always use unique passwords:**

```bash
# Generate strong password
openssl rand -base64 32
```

✅ **Keep API keys secure:**

- Use environment variables only
- Never log API keys
- Rotate keys regularly
- Limit API key permissions in Google Console

---

## 📚 Learn More

- [Full Deployment Guide](DEPLOYMENT.md)
- [Audit Report](AUDIT_REPORT.md)
- [Project Overview](doc/projectoverview.md)
- [Database Schema](Chronos/database/postgres_schema.py)
- [Decision Engine](Chronos/logic/engine.py)

---

## 💡 Tips

1. **Development Mode**: Set `DEBUG=true` in .env for better logging
2. **Database Admin**: Use PgAdmin at http://localhost:5050 for visual DB management
3. **Test Images**: Add sample images to test the adaptive selection
4. **Monitor Performance**: Check Docker stats: `docker stats`
5. **Code Style**: Format with Black: `black Chronos/`

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 8501 in use | Change in `docker-compose.yml` or `docker-compose down` |
| Container won't start | Check logs: `docker-compose logs app` |
| Database connection error | Verify `DATABASE_URL` in `.env` and postgres is running |
| Out of memory | Increase Docker memory limit or reduce image cache |
| Permissions denied | Use `sudo` or add user to docker group |

---

**Happy coding! 🎉**

For issues, check [GitHub Issues](https://github.com/yourusername/chronos/issues) or review the [DEPLOYMENT.md](DEPLOYMENT.md) guide.
