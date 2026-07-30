import { Box } from "@mui/material";
import DuplicatePairCard, {
  DuplicatePair,
} from "./DuplicatePairCard";

interface Props {
  pairs: DuplicatePair[];
  selectedId: number | null;
  onSelect: (pair: DuplicatePair) => void;
}

const DuplicatePairList = ({
  pairs,
  selectedId,
  onSelect,
}: Props) => {
  return (
    <Box>
      {pairs.map((pair) => (
        <DuplicatePairCard
          key={pair.groupId}
          pair={pair}
          selected={selectedId === pair.groupId}
          onClick={() => onSelect(pair)}
        />
      ))}
    </Box>
  );
};

export default DuplicatePairList;