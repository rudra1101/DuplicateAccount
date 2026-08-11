import { useEffect, useMemo, useState } from "react";

import {
  Alert,
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Pagination,
  Select,
  Stack,
  Typography,
} from "@mui/material";

import DuplicatePairCard, {
  DuplicatePair,
} from "./DuplicatePairCard";

interface Props {
  pairs: DuplicatePair[];
  selectedId: number | null;
  onSelect: (pair: DuplicatePair) => void;
}

type SortOption =
  | "confidence-desc"
  | "confidence-asc"
  | "duplicates-desc"
  | "username-asc";

const PAGE_SIZE = 10;

const DuplicatePairList = ({
  pairs,
  selectedId,
  onSelect,
}: Props) => {
  const [page, setPage] = useState(1);

  const [sortBy, setSortBy] =
    useState<SortOption>("confidence-desc");

  useEffect(() => {
    setPage(1);
  }, [pairs, sortBy]);

  const sortedPairs = useMemo(() => {
    const sorted = [...pairs];

    switch (sortBy) {
      case "confidence-asc":
        return sorted.sort(
          (first, second) =>
            first.highestConfidence -
            second.highestConfidence
        );

      case "duplicates-desc":
        return sorted.sort(
          (first, second) =>
            second.duplicates - first.duplicates
        );

      case "username-asc":
        return sorted.sort((first, second) =>
          first.primaryAccount.localeCompare(
            second.primaryAccount
          )
        );

      case "confidence-desc":
      default:
        return sorted.sort(
          (first, second) =>
            second.highestConfidence -
            first.highestConfidence
        );
    }
  }, [pairs, sortBy]);

  const totalPages = Math.max(
    1,
    Math.ceil(sortedPairs.length / PAGE_SIZE)
  );

  const visiblePairs = useMemo(() => {
    const startIndex = (page - 1) * PAGE_SIZE;

    return sortedPairs.slice(
      startIndex,
      startIndex + PAGE_SIZE
    );
  }, [sortedPairs, page]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  if (pairs.length === 0) {
    return (
      <Alert severity="info">
        No duplicate groups were found.
      </Alert>
    );
  }

  const firstVisibleRecord =
    (page - 1) * PAGE_SIZE + 1;

  const lastVisibleRecord = Math.min(
    page * PAGE_SIZE,
    sortedPairs.length
  );

  return (
    <Box>
      <Stack spacing={2} sx={{ mb: 2 }}>
        <Box>
          <Typography
            variant="subtitle2"
            color="text.secondary"
          >
            {pairs.length.toLocaleString()} duplicate group
            {pairs.length === 1 ? "" : "s"}
          </Typography>

          <Typography
            variant="caption"
            color="text.secondary"
          >
            Showing {firstVisibleRecord}–
            {lastVisibleRecord} of{" "}
            {sortedPairs.length.toLocaleString()}
          </Typography>
        </Box>

        <FormControl fullWidth size="small">
          <InputLabel>Sort Groups</InputLabel>

          <Select
            label="Sort Groups"
            value={sortBy}
            onChange={(event) =>
              setSortBy(
                event.target.value as SortOption
              )
            }
          >
            <MenuItem value="confidence-desc">
              Highest confidence first
            </MenuItem>

            <MenuItem value="confidence-asc">
              Lowest confidence first
            </MenuItem>

            <MenuItem value="duplicates-desc">
              Most duplicates first
            </MenuItem>

            <MenuItem value="username-asc">
              Username A–Z
            </MenuItem>
          </Select>
        </FormControl>
      </Stack>

      {visiblePairs.map((pair) => (
        <DuplicatePairCard
          key={pair.groupId}
          pair={pair}
          selected={selectedId === pair.groupId}
          onClick={() => onSelect(pair)}
        />
      ))}

      {totalPages > 1 && (
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            pt: 2,
            pb: 1,
          }}
        >
          <Pagination
            page={page}
            count={totalPages}
            size="small"
            color="primary"
            showFirstButton
            showLastButton
            onChange={(_, newPage) =>
              setPage(newPage)
            }
          />
        </Box>
      )}
    </Box>
  );
};

export default DuplicatePairList;