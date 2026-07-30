import {
  FormControl,
  MenuItem,
  Select,
  SelectChangeEvent,
} from "@mui/material";

interface Props {
  value: string;
  onChange: (value: string) => void;
}

const DashboardFilter = ({ value, onChange }: Props) => {
  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value);
  };

  return (
    <FormControl size="small" sx={{ width: 170 }}>
      <Select value={value} onChange={handleChange}>
        <MenuItem value="daily">Daily</MenuItem>
        <MenuItem value="weekly">Weekly</MenuItem>
        <MenuItem value="monthly">Monthly</MenuItem>
      </Select>
    </FormControl>
  );
};

export default DashboardFilter;