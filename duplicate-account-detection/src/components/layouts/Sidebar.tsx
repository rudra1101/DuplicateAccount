import {
  Drawer,
  Toolbar,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Box,
} from "@mui/material";

import { NavLink } from "react-router-dom";
import { navigationItems } from "../../types/navigation";

const drawerWidth = 250;

const Sidebar = () => {
  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: drawerWidth,
          boxSizing: "border-box",
          borderRight: "1px solid #e5e7eb",
        },
      }}
    >
      <Toolbar>
        <Typography
          variant="h6"
          sx={{
            fontWeight: 700,
            color: "#1976d2",
          }}
        >
          IdentityAI
        </Typography>
      </Toolbar>

      <Box sx={{ px: 1 }}>
        <List>
          {navigationItems.map((item) => {
            const Icon = item.icon;

            return (
              <ListItemButton
                key={item.id}
                component={NavLink}
                to={item.path}
                sx={{
                  borderRadius: 2,
                  mb: 1,
                }}
              >
                <ListItemIcon>
                  <Icon />
                </ListItemIcon>

                <ListItemText primary={item.title} />
              </ListItemButton>
            );
          })}
        </List>
      </Box>
    </Drawer>
  );
};

export default Sidebar;