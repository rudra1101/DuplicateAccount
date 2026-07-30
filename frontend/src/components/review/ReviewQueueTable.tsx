import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  Typography,
} from "@mui/material";

export interface DuplicateRecord {
  id: number;
  application: string;
  account1: string;
  account2: string;
  confidence: number;
}

interface Props {
  data?: DuplicateRecord[];
}

const ReviewQueueTable = ({ data = [] }: Props) => {
  return (
    <TableContainer
      component={Paper}
      elevation={0}
      sx={{ borderRadius: 2 }}
    >
      <Table>
        <TableHead>
          <TableRow>
            <TableCell><strong>ID</strong></TableCell>
            <TableCell><strong>Application</strong></TableCell>
            <TableCell><strong>Account 1</strong></TableCell>
            <TableCell><strong>Account 2</strong></TableCell>
            <TableCell><strong>Confidence</strong></TableCell>
            <TableCell align="center">
              <strong>Action</strong>
            </TableCell>
          </TableRow>
        </TableHead>

        <TableBody>
          {data.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} align="center">
                <Typography color="text.secondary">
                  No duplicate accounts found.
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            data.map((row) => (
              <TableRow key={row.id} hover>
                <TableCell>{row.id}</TableCell>

                <TableCell>{row.application}</TableCell>

                <TableCell>{row.account1}</TableCell>

                <TableCell>{row.account2}</TableCell>

                <TableCell>
                  <Chip
                    label={`${row.confidence}%`}
                    color={
                      row.confidence >= 90
                        ? "success"
                        : row.confidence >= 70
                        ? "warning"
                        : "error"
                    }
                    size="small"
                  />
                </TableCell>

                <TableCell align="center">
                  <Button
                    variant="contained"
                    size="small"
                  >
                    Review
                  </Button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default ReviewQueueTable;