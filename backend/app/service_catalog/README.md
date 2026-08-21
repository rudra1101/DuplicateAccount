# Service catalog

Each `*.json` file in this directory (except `system_roles.json`) defines one deployable service and its permissions.

At backend startup, `seed_rbac()` discovers these files and synchronizes service/permission metadata into SQLite. The database remains the runtime source of truth for role assignments.

To add a new service, create a new JSON file, for example `risk.json`:

```json
{
  "service": {
    "key": "risk",
    "name": "Risk Analytics",
    "description": "Risk analysis capabilities",
    "category": "Risk",
    "route": "/risk",
    "icon": "risk",
    "enabled": true,
    "sortOrder": 110
  },
  "permissions": [
    {"code": "risk.view", "name": "View risk analytics"},
    {"code": "risk.calculate", "name": "Run risk calculation"},
    {"code": "risk.manage", "name": "Manage risk configuration"}
  ],
  "defaultRoles": {
    "OWNER": "ALL",
    "ADMIN": "ALL",
    "USER": ["risk.view"]
  }
}
```

Then restart the backend or run:

```powershell
$env:PYTHONPATH="."
..\venv\Scripts\python.exe scripts\sync_service_catalog.py
```

Synchronization is additive and safe for administrator changes:

- new services are inserted;
- new permissions are inserted;
- names/descriptions/categories are refreshed;
- existing role assignments are preserved;
- defaults are applied to newly introduced permissions;
- removing a permission from a manifest does not delete it from the database.

API endpoints should still declare the permission they require (for example `require_permission("risk.view")`). The database decides whether the current user's role has that permission.
