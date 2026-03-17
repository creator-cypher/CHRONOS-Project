# CHRONOS Features & Enhancements Changelog

## Overview
This document details all features and enhancements added to CHRONOS during the latest development cycle, with rationale for each addition.

---

## 1. **Multi-User Authentication System**

### What Was Added
- **`auth.py` Module**: Complete authentication layer with bcrypt password hashing, login/registration flows, and session state management
- **Glassmorphic Login Screen**: Custom CSS injection for a frosted-glass centered card over animated gradient background
- **Profile Types**: Three user personas during registration:
  - **Standard**: Default experience with full feature access
  - **Kids**: Safety-filtered content with friendly UI
  - **Professional**: Advanced analytics and business-focused UI
- **Session State Management**: `st.session_state` remembers logged-in user and profile type throughout the session
- **User Database Schema**: New `users` table in both SQLite and PostgreSQL with fields for username, hashed password, profile type, and metadata

### Why It Was Added
1. **Privacy & Data Sovereignty**: Different users in the same household have isolated image libraries and preferences — essential for family use
2. **Academic Credibility**: Multi-user support is a core differentiator for "Privacy in the Home" thesis — demonstrates that CHRONOS respects boundaries
3. **Market Positioning**: Enables future commercial scaling (see render.yaml) where clients run this in their homes with multiple family members
4. **Trust & Compliance**: Bcrypt hashing ensures credentials are never stored in plaintext; supports GDPR/privacy frameworks

---

## 2. **Kids Safety Filter Intelligence**

### What Was Added
- **Automatic Safety Activation**: When `profile_type == 'Kids'`, forces `safety_filter = True` in the decision engine
- **Content Prioritization**: Kids mode boosts images tagged with `bright`, `cartoon`, `nature`, `educational`
- **Content Blocking**: Automatically blocks any images tagged with `dark`, `melancholic`, or `complex`
- **Engine Integration**: Logic embedded in `logic/engine.py` — filters applied at the candidate selection stage

### Why It Was Added
1. **Responsible AI**: Demonstrates algorithmic safety guardrails for minors — critical for academic papers and ethical AI discussions
2. **Parental Control**: Parents can confidently use CHRONOS knowing their children's content is filtered
3. **Award-Winning Detail**: Awwwards judges reward products that think about edge cases (children's safety); this shows maturity
4. **Regulatory Alignment**: Aligns with laws like COPPA (Children's Online Privacy Protection Act) that require age-appropriate content filtering

---

## 3. **Profile-Based Dynamic Theming**

### What Was Added
- **Theme Injection System**: CSS overrides in `auth.py` applied based on logged-in user's profile
- **Three Color Schemes**:
  - **Standard (Frosted Obsidian)**: Dark theme with gold accents (elegant, ambient)
  - **Kids (Sky Blue)**: Vibrant blue accent (`#2563eb`), softened 24px border-radius (friendly, approachable)
  - **Professional (Silver)**: Cool silver/gray palette with darker accents (business-focused)
- **Dynamic Sidebar**: Expanders, buttons, and text colors change per theme via CSS custom properties

### Why It Was Added
1. **Affective Computing**: The entire interface should "feel" different for different users — this is ambient computing
2. **UX Psychology**: Kids see softer colors and rounded corners; professionals see data-dense charts — visual design matches mental models
3. **Awwwards 2026 Criterion**: "The kind of detail that wins awards" — most apps have one theme; CHRONOS morphs its identity per user
4. **Accessibility**: Theme switching helps users with color sensitivity preferences (e.g., reduced contrast for dyslexia)

---

## 4. **User-Scoped Data Isolation**

### What Was Added
- **Foreign Key Relationships**: All tables (`images`, `context_logs`, `interactions`, `preferences`) now have `user_id` field
- **Query Layer Updates**: All database queries filtered by `current_user_id`
- **Sidebar Content**: "Image Library" and "Recent History" only show data belonging to logged-in user
- **Analytics Per User**: Each user sees only their own interaction stats, mood trends, and usage patterns

### Why It Was Added
1. **Data Privacy**: Fundamental requirement for multi-user systems — users should never see each other's data
2. **Trust Building**: Demonstrable data isolation is key for consumer trust; essential for master's thesis on home privacy
3. **Security Best Practice**: Prevents horizontal privilege escalation (User A viewing User B's images)
4. **Compliance**: Supports GDPR "right to deletion" — can purge one user's data without affecting others

---

## 5. **Database Schema Extensions**

### What Was Added

#### SQLite (schema.py)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    profile_type TEXT DEFAULT 'Standard',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```
- Added `user_id` field to `images`, `context_logs`, `interactions`, `preferences`
- Added migration columns: `analysis_error`, `retry_count`, `schedule_start`, `schedule_end`, `time_window`, `analysis_depth`, `analysis_focus`, `custom_prompt`

#### PostgreSQL (postgres_schema.py)
- Mirrored `users` table as SQLAlchemy ORM model
- Added relationships: `Image.user`, `ContextLog.user`, `ImageInteraction.user`
- Indexes on `(user_id, created_at)` for fast per-user queries

### Why It Was Added
1. **Dual-Mode Deployment**: SQLite for local dev, PostgreSQL for Render production — schema must support both
2. **Query Performance**: Indexes on `(user_id, created_at)` ensure fast filtering when showing user's recent images
3. **Migration Safety**: New columns added idempotently (wrapped in try/except) so existing deployments don't break
4. **Future Scalability**: Columns like `analysis_depth`, `analysis_focus`, `custom_prompt` prep for user-configurable AI behavior

---

## 6. **Privacy & Ethics Impact Assessment**

### What Was Added
- **New Document**: `doc/PRIVACY_ETHICS_ASSESSMENT.md` explaining:
  - How SQLite ensures local data sovereignty (no cloud sync)
  - Algorithmic implementation of Kids Safety Filter
  - Responsible AI principles applied in CHRONOS
  - Compliance with privacy regulations (GDPR, COPPA, etc.)

### Why It Was Added
1. **Academic Requirement**: Master's students submitting thesis/papers need formal ethical analysis
2. **Regulatory Evidence**: Demonstrates compliance-by-design; useful if product ever needs to meet legal audit
3. **Transparency**: Builds trust with end users by being explicit about how their data and children's data are protected
4. **Award Credibility**: Awwwards entries increasingly require ethics statements; shows the project is thoughtful

---

## 7. **Dependencies Updated**

### What Was Added
- **`bcrypt==5.1.0`**: Added to both `Chronos/requirements.txt` and root `requirements.txt`
  - Secure password hashing for authentication
  - Industry-standard for credential storage
  - Required by `auth.py` module

### Why It Was Added
1. **Security Standard**: Bcrypt is the OWASP-recommended algorithm for password hashing (resistant to GPU brute-force)
2. **No Plaintext Credentials**: Users' passwords are never stored in the database — only bcrypt hashes
3. **Cross-Environment Consistency**: Both Docker and Render deployments have identical dependencies

---

## 8. **Glassmorphism UI for Login**

### What Was Added
- **Custom CSS Injection**: Backdrop blur, semi-transparent card, animated gradient background
- **Centered Form**: Login/register form positioned in the viewport center with responsive padding
- **Animation**: Slow-moving gradient shift creates ambient, welcoming feel

### Why It Was Added
1. **First Impression**: Login screen is the first thing users see — glassmorphism is 2024/2026 design trend
2. **Brand Differentiation**: Most apps have boring login forms; CHRONOS's is visually striking
3. **Awwwards Aesthetic**: Glassmorphism + animated background = entry-level awwward category
4. **Mobile-Responsive**: Padding and blur scale down on mobile without breaking layout

---

## 9. **Deployment Documentation Reorganization**

### What Was Added
- **Moved Files**:
  - `DEPLOYMENT.md` → `doc/DEPLOYMENT.md`
  - `DEPLOYMENT_SUMMARY.md` → `doc/DEPLOYMENT_SUMMARY.md`
- **Rationale**: Cleaner project structure — deployment details are reference docs, not top-level project files

### Why It Was Added
1. **Project Organization**: Separates implementation docs (in `doc/`) from core code and README
2. **Maintainability**: Easier for new contributors to find reference material in a dedicated folder
3. **Professional Structure**: GitHub best practices recommend keeping root directory minimal

---

## Summary Table

| Feature | Added | Why |
|---------|-------|-----|
| Multi-user auth | `auth.py` | Family isolation + academic credibility |
| Kids safety filter | `engine.py` | Responsible AI + regulatory compliance |
| Dynamic theming | CSS injection | Affective computing + award-winning UX |
| Data scoping | Schema/queries | Privacy + security best practice |
| Bcrypt hashing | Dependencies | OWASP-standard credential security |
| Privacy assessment | `PRIVACY_ETHICS_ASSESSMENT.md` | Academic thesis + regulatory transparency |
| Glassmorphism UI | CSS + HTML | Modern aesthetics + brand differentiation |
| Schema extensions | PostgreSQL + SQLite | Dual-mode deployment + future scalability |

---

## Implementation Status

✅ All features committed and pushed to `main` branch
✅ Render auto-deployment triggered
✅ Docker image includes all dependencies
✅ Database migrations idempotent (safe for existing deployments)

---

## Next Steps (Optional Enhancements)

1. **Social Features**: Allow users to share preset themes with family members
2. **Parental Dashboards**: Parents can view children's image interaction history (with consent)
3. **AI Personalization**: Each profile type gets different Gemini prompt engineering (Kids = simpler descriptions, Professional = detailed insights)
4. **Usage Analytics**: Track which profile types use which features most — data for product decisions
