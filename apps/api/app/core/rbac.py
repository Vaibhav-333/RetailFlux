"""Role-Based Access Control — permission matrix for dept-level analytics access.

Each role can access analytics for their own department + the CEO summary.
CEO and ADMIN can access everything. This is the source of truth for authz.
"""
from app.models.user import UserRole

# Maps role → set of analytics departments they can access.
# CEO + ADMIN can access all departments.
ROLE_DEPT_ACCESS: dict[str, set[str]] = {
    UserRole.CEO.value: {"sales", "marketing", "operations", "finance", "procurement", "summary"},
    UserRole.ADMIN.value: {"sales", "marketing", "operations", "finance", "procurement", "summary"},
    UserRole.SALES.value: {"sales", "summary"},
    UserRole.MARKETING.value: {"marketing", "summary"},
    UserRole.FINANCE.value: {"finance", "summary"},
    UserRole.OPERATIONS.value: {"operations", "summary"},
    UserRole.PROCUREMENT.value: {"procurement", "summary"},
}

# Roles that can access admin features (observability, audit, cache, user mgmt)
ADMIN_ROLES: set[str] = {UserRole.CEO.value, UserRole.ADMIN.value}

# Roles that can upload data per department
ROLE_UPLOAD_ACCESS: dict[str, set[str]] = {
    UserRole.CEO.value: {"sales", "marketing", "operations", "finance", "procurement"},
    UserRole.ADMIN.value: {"sales", "marketing", "operations", "finance", "procurement"},
    UserRole.SALES.value: {"sales"},
    UserRole.MARKETING.value: {"marketing"},
    UserRole.FINANCE.value: {"finance"},
    UserRole.OPERATIONS.value: {"operations"},
    UserRole.PROCUREMENT.value: {"procurement"},
}


def can_access_dept(role: str, dept: str) -> bool:
    """Check if a role has permission to access a department's analytics."""
    allowed = ROLE_DEPT_ACCESS.get(role, set())
    return dept in allowed


def can_upload_dept(role: str, dept: str) -> bool:
    """Check if a role can upload data for a department."""
    allowed = ROLE_UPLOAD_ACCESS.get(role, set())
    return dept in allowed


def is_admin(role: str) -> bool:
    """Check if a role has admin privileges."""
    return role in ADMIN_ROLES
