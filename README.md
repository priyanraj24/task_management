# Employee Task Management System

A role-based task management REST API built with FastAPI, SQLAlchemy, and PostgreSQL.

## Roles

- **Admin** - Full access. Manages users, projects, and assignments.
- **Manager** - Manages assigned projects and their tasks. Can assign employees.
- **Employee** - Views and updates status of assigned tasks. Uploads attachments.

## Setup

```bash
# Create virtual environment
python -m venv venv

# Activate
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

## Environment Variables

```
DATABASE_URL=postgresql://postgres:password@localhost:5432/task_management
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## API Endpoints

### Auth
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/auth/register` | Public | Register (default role: employee) |
| POST | `/auth/login` | Public | Login, returns JWT |
| GET | `/auth/me` | Authenticated | Current user profile |

### Users
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/users/` | Admin | List users (filter: name, email, role) |
| GET | `/users/{id}` | Admin | Get user |
| PUT | `/users/{id}` | Admin | Update user |
| DELETE | `/users/{id}` | Admin | Soft delete user |

### Projects
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/projects/` | Admin, Manager | Create project |
| GET | `/projects/` | All (scoped) | List projects (filter: name, status) |
| GET | `/projects/{id}` | All (scoped) | Get project |
| PUT | `/projects/{id}` | Admin, Manager | Update project |
| DELETE | `/projects/{id}` | Admin | Soft delete project |
| POST | `/projects/{id}/assign` | Admin, Manager | Assign user to project |
| DELETE | `/projects/{id}/unassign` | Admin, Manager | Remove user from project |
| GET | `/projects/{id}/tasks` | All (scoped) | List project tasks |
| POST | `/projects/{id}/tasks` | Admin, Manager | Create task |

### Tasks
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/tasks/` | All (scoped) | List tasks (filter: title, status, priority, project_id, employee_id) |
| GET | `/tasks/{id}` | All (scoped) | Get task |
| PUT | `/tasks/{id}` | Admin, Manager | Update task |
| DELETE | `/tasks/{id}` | Admin | Soft delete task |
| PATCH | `/tasks/{id}/status` | All (scoped) | Update status |
| POST | `/tasks/{id}/assign` | Admin, Manager | Assign employee to task |
| DELETE | `/tasks/{id}/unassign` | Admin, Manager | Remove employee from task |
| GET | `/tasks/{id}/history` | All (scoped) | Status change history |
| POST | `/tasks/{id}/attachments` | All (scoped) | Upload file |
| GET | `/tasks/{id}/attachments` | All (scoped) | List attachments |
| DELETE | `/tasks/{id}/attachments/{id}` | All (scoped) | Delete attachment |

### Dashboard
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/dashboard/summary` | All (scoped) | Project and task stats |

## Database Schema

| Table | Description |
|-------|-------------|
| `users` | User accounts with roles |
| `projects` | Projects with status and dates |
| `project_users` | Project assignments (many-to-many) |
| `tasks` | Tasks linked to projects |
| `task_assignments` | Task assignments (many-to-many) |
| `task_history` | Status change audit log |
| `attachments` | File attachments on tasks |

## Migrations

| # | Migration |
|---|-----------|
| 001 | Create users table |
| 002 | Create projects table |
| 003 | Create project_users table |
| 004 | Create tasks table |
| 005 | Create task_assignments table |
| 006 | Create task_history table |
| 007 | Create attachments table |

```bash
alembic upgrade head      # Apply all
alembic downgrade -1      # Rollback last
alembic current           # Current version
```

## Authorization Rules

- Admin can assign managers and employees to projects
- Manager can only assign employees to their own projects
- Manager is auto-added to project_users when they create a project
- Employee must be a project member before being assigned a task
- Employees cannot use the employee_id filter in task listing
- `created_by` is audit only — access is determined by `project_users` assignments
- Deleting a user nullifies their `created_by` and `assigned_by` references, cascades to project and task assignments
- Deleting a project cascades to its assignments, tasks, task assignments, and attachments
- Unassigning an employee from a project removes their task assignments in that project
- Task due date must fall within project start and end dates
- Tasks cannot be updated when project is completed or cancelled
- Task history is preserved on delete

## Soft Delete

All deletes are soft deletes (`is_deleted`, `deleted_at`). Unique fields are mangled on delete to allow reuse. Reassigning a previously unassigned user restores the existing record.

## Response Format

```json
{
    "success": true,
    "message": "...",
    "data": { ... },
    "error": null
}
```

## Validation

| Field | Rules |
|-------|-------|
| Name | Min 3, max 255 characters |
| Password | 8-20 chars, uppercase, lowercase, digit, special character |
| Email | Valid format, unique |
| Project status | planned, active, completed, cancelled |
| Task status | todo, in_progress, completed, blocked |
| Task priority | low, medium, high, critical |
| Due date | Cannot be in the past (on create) |
| File upload | pdf, png, jpg, txt; max 10MB |
