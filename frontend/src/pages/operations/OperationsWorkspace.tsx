import { Box, Paper, Tab, Tabs } from "@mui/material";
import { useState } from "react";

import Operations from "./Operations";
import SystemStatus from "./SystemStatus";

const OperationsWorkspace = () => {
  const [tab, setTab] = useState(0);

  return (
    <>
      <Box sx={{ px: { xs: 2, md: 3 }, pt: { xs: 2, md: 3 } }}>
        <Paper variant="outlined" sx={{ borderRadius: 3, px: 1 }}>
          <Tabs
            value={tab}
            onChange={(_, value: number) => setTab(value)}
            aria-label="Operations workspace tabs"
          >
            <Tab label="Executions" />
            <Tab label="System Status" />
          </Tabs>
        </Paper>
      </Box>

      {tab === 0 ? <Operations /> : <SystemStatus />}
    </>
  );
};

export default OperationsWorkspace;
