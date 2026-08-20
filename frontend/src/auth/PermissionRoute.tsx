import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";

interface Props {
  anyOf: string[];
}

export default function PermissionRoute({ anyOf }: Props) {
  const { user, hasPermission } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!anyOf.some((permission) => hasPermission(permission))) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
