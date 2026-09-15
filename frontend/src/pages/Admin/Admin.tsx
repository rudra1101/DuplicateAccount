import { Box, Stack, Typography } from "@mui/material";
import { useMemo } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";
import BrandingSettings from "./BrandingSettings";
import RoleManagement from "./RoleManagement";
import UserManagement from "./UserManagement";

type AdminSection = "users" | "roles" | "branding";

export default function Admin() {
  const { hasPermission } = useAuth();
  const location = useLocation();
  const canUsers = hasPermission("user.view");
  const canRoles = hasPermission("role.view");
  const canBranding = hasPermission("settings.manage");

  const allowedSections = useMemo<AdminSection[]>(() => {
    const sections: AdminSection[] = [];
    if (canUsers) sections.push("users");
    if (canRoles) sections.push("roles");
    if (canBranding) sections.push("branding");
    return sections;
  }, [canUsers, canRoles, canBranding]);

  const routeSection = location.pathname.split("/").filter(Boolean).at(-1) as AdminSection | undefined;

  if (location.pathname === "/platform-admin") {
    const firstSection = allowedSections[0];
    return firstSection ? <Navigate to={`/platform-admin/${firstSection}`} replace /> : null;
  }

  const section = allowedSections.includes(routeSection as AdminSection)
    ? (routeSection as AdminSection)
    : allowedSections[0];

  if (!section) return null;

  const sectionCopy: Record<AdminSection, { title: string; description: string }> = {
    users: {
      title: "Users",
      description: "Manage IdentityAI users, status, and role assignments.",
    },
    roles: {
      title: "Roles & Permissions",
      description: "Manage platform roles and granular permissions across IdentityAI domains and features.",
    },
    branding: {
      title: "Branding",
      description: "Manage the global IdentityAI logo and customer color palette.",
    },
  };

  return (
    <Box>
      <Stack spacing={0.5} sx={{ mb: 3 }}>
        <Typography variant="h5" fontWeight={700}>{sectionCopy[section].title}</Typography>
        <Typography color="text.secondary">{sectionCopy[section].description}</Typography>
      </Stack>

      {section === "users" && canUsers && <UserManagement />}
      {section === "roles" && canRoles && <RoleManagement />}
      {section === "branding" && canBranding && <BrandingSettings />}
    </Box>
  );
}
