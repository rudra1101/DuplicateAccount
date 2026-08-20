# Patch guide for the current GitHub code

The current integrations page always renders **Add Integration**, and IntegrationCard always renders **Test/Edit/Delete**. Change those because USER must not see management actions.

## Integrations.tsx

Import:
```tsx
import { useAuth } from "../../auth/AuthContext";
```

Inside component:
```tsx
const { isAdmin } = useAuth();
```

Wrap Add Integration:
```tsx
{isAdmin && (
  <Button
    variant="contained"
    startIcon={<AddIcon />}
    onClick={() => navigate("/integrations/new")}
  >
    Add Integration
  </Button>
)}
```

Pass:
```tsx
<IntegrationCard
  ...
  canManage={isAdmin}
/>
```

## IntegrationCard.tsx

Add:
```tsx
canManage: boolean;
```

Keep these visible for both roles:
- Run Now
- Schedule
- History

Wrap these in `{canManage && (...)}`:
- Test
- Edit
- Delete

## Sidebar.tsx

Import `useAuth`.

Add `adminOnly: true` to:
- Admin
- User Management

Filter:
```tsx
const visibleItems = menuItems.filter(
  item => !item.adminOnly || isAdmin
);
```

Add:
```tsx
{
  text: "User Management",
  icon: <AdminPanelSettingsIcon />,
  path: "/users",
  adminOnly: true,
}
```

## AppRoutes.tsx

Protect:
```tsx
<Route element={<RoleRoute roles={["ADMIN"]} />}>
  <Route path="admin" element={<Admin />} />
  <Route path="users" element={<UserManagement />} />
  <Route path="integrations/new" element={<AddIntegration />} />
  <Route path="integrations/:integrationId/edit" element={<AddIntegration />} />
</Route>
```

USER entering those URLs manually is redirected to `/`.

## integrations.py

Import:
```python
from app.auth import require_roles
```

ADMIN-only endpoint dependency:
```python
_user = Depends(require_roles("ADMIN"))
```

Apply to:
- POST `/integrations/`
- PUT `/integrations/{id}`
- DELETE `/integrations/{id}`
- POST `/integrations/{id}/test`
- connector configuration endpoints

ADMIN + USER:
```python
_user = Depends(require_roles("ADMIN", "USER"))
```

Apply to:
- list/view integrations
- POST `/integrations/{id}/run`
- execution history

## job_schedules.py

All schedule operations:
```python
_user = Depends(require_roles("ADMIN", "USER"))
```

## main.py

Register:
```python
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.auth.middleware import authentication_middleware
```

Then:
```python
app.middleware("http")(authentication_middleware)
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
```

## db_models/__init__.py

Import:
```python
from app.db_models.user import UserRecord
```

and include `"UserRecord"` in `__all__`.

## Review behavior

ADMIN:
- Create USER/ADMIN
- Add Integration
- Test/Edit/Delete
- Run/Schedule

USER:
- no Admin/User Management
- no Add Integration
- no Test/Edit/Delete
- cannot manually navigate to admin routes
- Run/Schedule/History remain available
- direct admin-only API call returns 403
