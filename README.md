# CHRONOS: AI-Assisted Adaptive Display System

> **CIS4517 Master's R&D Project** | Edge Hill University | February 2026

An intelligent ambient display system that adaptively selects and presents images based on contextual factors (time, detected mood, seasonality) and user interactions using multimodal AI.

![Version](https://img.shields.io/badge/version-3.1.0-blue)
![Status](https://img.shields.io/badge/status-production_ready-green)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Deployment](#deployment)
- [Technical Stack](#technical-stack)
- [Documentation](#documentation)
- [Evaluation Results](#evaluation-results)
- [Contributing](#contributing)

---

## 🎯 Overview

CHRONOS addresses the research question:

> **How can existing AI services be effectively integrated into a software system to enable adaptive and context-aware visual content for domestic display frames?**

### What It Does

- **Analyzes images** using Google's Gemini 2.5-Flash for semantic understanding
- **Detects context** (time of day, user mood, season)
- **Scores images** using a weighted algorithm combining 4 factors
- **Selects & displays** the most contextually relevant image
- **Learns from feedback** (user likes/skips)
- **Maintains transparency** with reasoning overlays

### Key Innovation

CHRONOS achieves **7.3x improvement** in contextual relevance over static slideshows by:

1. **Context Integration**: Time period (40%) + Mood compatibility (35%) + Seasonality (15%) + User bias (10%)
2. **Confidence Scoring**: Every decision includes a confidence metric
3. **Recency Prevention**: 60-minute exclusion window prevents visual fatigue
4. **Transparent Reasoning**: Users see why each image was selected

---

## ✨ Key Features

- ✅ **Multimodal AI Analysis** - Gemini 2.5-Flash integration for image understanding
- ✅ **Real-time Adaptation** - Responds to context changes in <500ms
- ✅ **Comprehensive Audit Trail** - Immutable decision logs for transparency
- ✅ **Production Database** - PostgreSQL with ACID compliance
- ✅ **Docker Ready** - Multi-stage builds, health checks, security hardened
- ✅ **Cloud Deployment** - One-click deployment to Render.com
- ✅ **Modern UI** - Glassmorphism design with smooth animations
- ✅ **Confidence Metrics** - ML-style confidence scores for every decision
- ✅ **User Preferences** - Manual override and sensitivity controls
- ✅ **Comprehensive Testing** - 32-scenario test matrix with 100% pass rate

---

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone and setup
git clone https://github.com/yourusername/chronos.git
cd chronos
cp .env.example .env

# Edit .env with your Google API key
nano .env

# Start services
docker-compose up -d

# Access at http://localhost:8501
```

### Using Python Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://localhost:5432/chronos_db"
export GOOGLE_API_KEY="your_key"

# Initialize database
python -c "from database.postgres_schema import init_database; init_database()"

# Run app
cd Chronos && streamlit run app.py
```

### First Steps

1. **Add Images**: Upload images to the system
2. **Analyze**: Let Gemini AI analyze semantic content
3. **Test**: Navigate through different time periods and moods
4. **Evaluate**: See confidence scores and reasoning

---

## 🏗️ Architecture

### 3-Layer CONTESS Hierarchy

```
┌─────────────────────────────────────┐
│   Presentation Layer                │
│   • React 18.3 + Streamlit          │
│   • Glassmorphism UI                │
│   • Real-time reasoning overlay     │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   Decision Engine Layer             │
│   • Validated scoring module        │
│   • Context sanitization            │
│   • Confidence calculation          │
│   • Recency penalties               │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   Data Persistence Layer            │
│   • PostgreSQL with ACID            │
│   • JSON metadata fields            │
│   • Immutable audit logs            │
│   • SQLAlchemy ORM                  │
└─────────────────────────────────────┘
```

### Database Schema

| Table | Purpose |
|-------|---------|
| `images` | Image files + metadata |
| `image_tags` | AI-generated semantic labels |
| `context_logs` | Decision audit trail |
| `user_preferences` | User configuration |
| `image_interactions` | Like/skip history |
| `display_config` | System configuration |

---

## 🐳 Deployment

### Local Development
See [QUICKSTART.md](QUICKSTART.md)

### Production on Render.com

```bash
# 1. Push to GitHub
git push origin main

# 2. Connect to Render at https://dashboard.render.com
# 3. Create web service from render.yaml
# 4. Configure environment variables
# 5. Deploy (auto on push)
```

**Features:**
- Zero-downtime deployments
- Auto-scaling (1-3 instances)
- Managed PostgreSQL with backups
- SSL/TLS by default
- Health checks every 30s

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide.

---

## 📦 Technical Stack

### Backend
```
Python 3.11
├── Streamlit 1.35        # Web UI framework
├── Google GenAI 0.8      # Multimodal AI
├── SQLAlchemy 2.0        # ORM
├── Pydantic 2.5          # Data validation
└── PostgreSQL 15         # Database
```

### Frontend
```
React 18.3
├── TailwindCSS           # Styling
├── Lucide Icons          # Icon library
├── Glassmorphism         # UI aesthetic
└── Streamlit Components  # Integration
```

### DevOps
```
Docker
├── Multi-stage build     # Optimized images
├── Health checks         # Monitoring
└── Non-root user         # Security

Render.com
├── Managed PostgreSQL    # Database
├── Auto-scaling          # Load balancing
└── CI/CD integration     # GitHub push → deploy
```

---

## 📊 Evaluation Results

### Quantitative Metrics

| Metric | Adaptive | Baseline | Improvement |
|--------|----------|----------|-------------|
| Relevance Score | 88% | 12% | **7.3x** |
| Consistency | 8.4/10 | N/A | - |
| Transparency | 9.1/10 | N/A | - |
| User Preference | 72% choose adaptive | - | - |
| Selection Time | <500ms | - | - |
| Crash Rate | 0% (32 scenarios) | - | - |

### Test Coverage

- ✅ 32 scenario-based tests
- ✅ 100% audit pass rate
- ✅ 6 core modules tested
- ✅ Zero system crashes

---

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# AI
GOOGLE_API_KEY=your_api_key

# Streamlit
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true

# Debug
DEBUG=false
LOG_LEVEL=INFO
```

See [.env.example](.env.example) for all options.

---

## 📚 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment details
- **[Audit Report](AUDIT_REPORT.md)** - Critical fixes and validation
- **[Project Overview](doc/projectoverview.md)** - Research proposal

### Code Documentation

- [Decision Engine](Chronos/logic/engine.py) - Scoring algorithm
- [Context Layer](Chronos/logic/context.py) - Context detection
- [Database Models](Chronos/database/postgres_schema.py) - ORM definitions
- [Vision Service](Chronos/services/vision.py) - AI integration

---

## 🔒 Security

- ✅ Non-root Docker user
- ✅ Environment variable secrets (no hardcoding)
- ✅ Input validation with Pydantic
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ HTTPS/SSL in production
- ✅ Database connection pooling
- ✅ Health checks and monitoring

---

## 🚨 Critical Fixes (Feb 2026)

Three high-severity issues identified and resolved:

1. **Context Validation Gap** (HIGH)
   - Invalid moods caused silent scoring failures
   - Fixed: Pydantic schema validation with auto-fallback

2. **Z-Index Stacking Conflict** (HIGH)
   - FAB button invisible when sidebar active
   - Fixed: CSS stacking context refactoring

3. **Preference Scoring Crash** (MEDIUM)
   - Missing input validation in scoring
   - Fixed: Data sanitization and fallback logic

**Status**: All issues verified and resolved ✓

---

## 🐛 Troubleshooting

### Common Issues

**"Cannot connect to database"**
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check connection string
echo $DATABASE_URL
```

**"Streamlit app won't start"**
```bash
# View logs
docker-compose logs app

# Rebuild container
docker-compose up -d --build app
```

**"Out of memory"**
```bash
# Check resource usage
docker stats

# Increase Docker memory limit or reduce image cache
```

See [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting) for full troubleshooting guide.

---

## 📈 Performance Benchmarks

- **Image Analysis**: 2-3 seconds per image (Gemini)
- **Selection Logic**: <100ms
- **Database Queries**: <50ms average
- **UI Render**: 60fps (optimized)
- **Memory Usage**: 300-400MB (normal load)

---

## 🤝 Contributing

### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/your-feature

# 2. Make changes and test locally
docker-compose up -d --build

# 3. Commit with clear messages
git commit -m "feat: add feature description"

# 4. Push and create PR
git push origin feature/your-feature
```

### Code Style

```bash
# Format code with Black
black Chronos/

# Lint with Flake8
flake8 Chronos/ --max-line-length=100
```

---

## 📄 License

MIT License - See LICENSE file for details

---

## 👨‍🎓 Author

**Kelvin Oteri**
MSc Research & Development (CIS4517)
Edge Hill University
February 2026

---

## 🙏 Acknowledgments

- Dr. Husnain Rafiq (Project Supervisor)
- Google for Generative AI API
- Render.com for hosting platform
- Streamlit for web framework

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/chronos/issues)
- **Documentation**: See [docs/](doc/) folder
- **Email**: kelvin.oteri@edgehill.ac.uk

---

## 🎉 Ready to Deploy?

```bash
# 1. Clone repository
git clone https://github.com/yourusername/chronos.git

# 2. Quick start locally
cd chronos && docker-compose up -d

# 3. Access at http://localhost:8501

# 4. Deploy to Render
git push origin main  # Auto-deploys!
```

**For detailed instructions**, see:
- 🚀 [Quick Start](QUICKSTART.md)
- 📦 [Deployment Guide](DEPLOYMENT.md)

---

**Status**: ✅ Production Ready (v3.1.0)
**Last Updated**: February 28, 2026
