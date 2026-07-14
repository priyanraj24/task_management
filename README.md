# Employee Task Management System

A role-based task management REST API built with FastAPI, SQLAlchemy, and PostgreSQL.

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- pip

## Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd Employee-Task-Management-System-v1

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment variables
cp .env.example .env
# Edit .env with your database credentials and secret key

# 6. Create PostgreSQL database
# Open psql or pgAdmin and run:
# CREATE DATABASE task_management;

# 7. Run database migrations
alembic upgrade head

# 8. Start the server
uvicorn app.main:app --reload

# 9. Create the first admin user
# Register via POST /auth/register (default role is "employee")
# Then promote to admin in the database:
# UPDATE users SET role = 'admin' WHERE email = 'your-email@example.com';
```

The API will be available at `http://localhost:8000`

Swagger docs: `http://localhost:8000/docs`

## Environment Variables

Copy `.env.example` to `.env` and update the values:

```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/task_management
SECRET_KEY=generate-using-python-c-import-secrets-print-secrets-token-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Project Structure

```
app/
├── main.py                  # FastAPI app, CORS, exception handlers
├── config.py                # Environment variable loading and validation
├── database.py              # SQLAlchemy engine, session, Base, soft delete
├── response.py              # Standardized API response format
│
├── auth/                    # Authentication & Authorization
│   ├── routes.py            # POST /auth/register, /auth/login, GET /auth/me
│   ├── controller.py        # Login/register business logic
│   ├── service.py           # Password hashing, JWT, user queries
│   ├── dependencies.py      # get_current_user, require_roles
│   └── schemas.py           # UserRegister, UserLogin
│
├── users/                   # User Management (admin only)
│   ├── models.py            # User model
│   ├── routes.py            # GET/PUT/DELETE /users
│   ├── controller.py        # User CRUD logic
│   ├── service.py           # User queries
│   └── schemas.py           # UserUpdate
│
├── projects/                # Project Management
│   ├── models.py            # Project model
│   ├── routes.py            # CRUD /projects, /projects/{id}/tasks, /assign
│   ├── controller.py        # Project CRUD + assignment logic
│   ├── service.py           # Project queries
│   └── schemas.py           # ProjectCreate, ProjectUpdate, ProjectAssign
│
├── tasks/                   # Task Management
│   ├── models.py            # Task, TaskHistory, Attachment models
│   ├── routes.py            # CRUD /tasks, /status, /history, /attachments
│   ├── controller.py        # Task CRUD + file upload logic
│   ├── service.py           # Task, history, attachment queries
│   └── schemas.py           # TaskCreate, TaskUpdate, TaskStatusUpdate
│
├── dashboard/               # Dashboard
│   ├── routes.py            # GET /dashboard/summary
│   ├── controller.py        # Summary logic
│   └── service.py           # Raw SQL CTE queries (PostgreSQL)
│
migrations/                  # Alembic migrations
├── env.py
├── versions/
│   ├── 001_create_users_table.py
│   ├── 002_create_projects_table.py
│   ├── 003_create_tasks_and_task_history_tables.py
│   ├── 004_create_attachments_table.py
│   ├── 005_add_soft_delete_columns.py
│   ├── 006_add_assigned_to_to_projects.py
│   └── 007_add_updated_at_columns.py
```

## Database Migrations

All schema changes go through **Alembic** migrations. Tables are never created via `Base.metadata.create_all()`.

```bash
# Apply all migrations
alembic upgrade head

# Rollback the last migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base

# View current migration status
alembic current

# View migration history
alembic history

# Create a new migration after modifying models
alembic revision --autogenerate -m "describe your change"
```

### Migration History

| Migration | Description |
|-----------|-------------|
| `001` | Create `users` table |
| `002` | Create `projects` table |
| `003` | Create `tasks` and `task_history` tables |
| `004` | Create `attachments` table |
| `005` | Add soft delete columns (`is_deleted`, `deleted_at`) to all tables |
| `006` | Add `assigned_to` column to projects (manager assignment) |
| `007` | Add `updated_at` column to users, projects, tasks |

## Database Relationships

```
User
 ├── created_projects       → Projects created by this user
 ├── assigned_projects      → Projects assigned to this manager
 ├── created_tasks          → Tasks created by this user
 ├── assigned_tasks         → Tasks assigned to this user
 └── uploaded_attachments   → Attachments uploaded by this user

Project
 ├── creator                → User who created the project
 ├── manager                → User (manager) assigned to the project
 └── tasks                  → Tasks under this project

Task
 ├── project                → Parent project
 ├── creator                → User who created the task
 ├── assignee               → User assigned to the task
 ├── attachments            → File attachments
 └── history                → Status change audit log

TaskHistory (immutable audit log)
 └── task                   → Parent task

Attachment
 ├── task                   → Parent task
 └── uploader               → User who uploaded the file
```

## Authorization Rules

| Role | Projects | Tasks | Users |
|------|----------|-------|-------|
| **Admin** | Full CRUD on all, assign to manager | Full CRUD on all | View, update, delete |
| **Manager** | View/update assigned projects | Create/assign tasks under assigned projects | - |
| **Employee** | View projects with assigned tasks | View assigned tasks, update status only | - |

- Admin cannot edit/delete other admins or change their own role
- All unauthorized access returns `403 Forbidden`
- All update endpoints support partial updates (send only fields you want to change)

## API Endpoints

### Auth
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/auth/register` | Public | Register a new user |
| POST | `/auth/login` | Public | Login and get JWT token |
| GET | `/auth/me` | Authenticated | Get current user profile |

### Users (Admin only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/` | List all users (paginated) |
| GET | `/users/{id}` | Get user details |
| PUT | `/users/{id}` | Update user (name, email, role) |
| DELETE | `/users/{id}` | Soft delete user |

### Projects
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/projects/` | Admin, Manager | Create project |
| GET | `/projects/` | All (scoped) | List projects |
| GET | `/projects/{id}` | All (scoped) | Get project details |
| PUT | `/projects/{id}` | Admin, Manager | Update project |
| PATCH | `/projects/{id}/assign` | Admin | Assign project to a manager |
| GET | `/projects/{id}/tasks` | All (scoped) | List tasks under project |
| POST | `/projects/{id}/tasks` | Admin, Manager | Create task under project |
| DELETE | `/projects/{id}` | Admin | Soft delete project |

### Tasks
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/tasks/` | All (scoped) | List tasks (filter: status, priority, project_id) |
| GET | `/tasks/{id}` | All (scoped) | Get task details |
| PUT | `/tasks/{id}` | Admin, Manager | Update task |
| PATCH | `/tasks/{id}/status` | All (scoped) | Update task status only |
| DELETE | `/tasks/{id}` | Admin | Soft delete task |
| GET | `/tasks/{id}/history` | All (scoped) | Get status change history |
| POST | `/tasks/{id}/attachments` | All (scoped) | Upload file (pdf, png, jpg, txt; max 10MB) |
| GET | `/tasks/{id}/attachments` | All (scoped) | List attachments |
| DELETE | `/tasks/{id}/attachments/{id}` | All (scoped) | Soft delete attachment |

### Dashboard
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/dashboard/summary` | All (scoped) | Aggregated project and task stats |

## API Response Format

All responses follow a standardized format:

**Success:**
```json
{
    "success": true,
    "message": "Task created successfully",
    "data": { ... },
    "error": null
}
```

**Error:**
```json
{
    "success": false,
    "message": "Project not found",
    "data": null,
    "error": null
}
```

**Validation Error (422):**
```json
{
    "success": false,
    "message": "Validation error",
    "data": null,
    "error": [
        { "field": "priority", "message": "Invalid priority. Must be one of: low, medium, high, critical" }
    ]
}
```

## Validation Rules

| Field | Rules |
|-------|-------|
| User name | Min 3, max 255; letters and spaces only |
| Project/task name | Min 3, max 255; letters, numbers, spaces, hyphens, underscores |
| Password | Min 8, max 20; must include uppercase, lowercase, digit, special character |
| Email | Valid email format, unique |
| Project status | planned, active, completed, cancelled |
| Task status | todo, in_progress, completed, blocked |
| Task priority | low, medium, high, critical |
| Due date | Cannot be in the past (on create) |
| File upload | pdf, png, jpg, txt only; max 10MB; blocked on completed/blocked tasks and expired/cancelled projects |
| Description | Optional, max 255 characters |
| Assigned to (project) | Must be a user with manager role |
| Assigned to (task) | Must be a user with employee role |

## Soft Delete

Records are never hard-deleted. All delete operations set `is_deleted = true` and `deleted_at` timestamp. All queries automatically filter out soft-deleted records. Unique fields (like email) are mangled on delete to free the value for reuse.

## Supported Statuses

**Project:** planned, active, completed, cancelled

**Task:** todo, in_progress, completed, blocked

**Priority:** low, medium, high, critical

**Roles:** admin, manager, employee
