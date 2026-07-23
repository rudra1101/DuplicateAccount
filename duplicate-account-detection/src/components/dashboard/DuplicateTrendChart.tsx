import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const data = [
  { day: "Mon", duplicates: 20 },
  { day: "Tue", duplicates: 35 },
  { day: "Wed", duplicates: 25 },
  { day: "Thu", duplicates: 40 },
  { day: "Fri", duplicates: 55 },
  { day: "Sat", duplicates: 30 },
  { day: "Sun", duplicates: 15 },
];

const DuplicateTrendChart = () => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="day" />
        <YAxis />
        <Tooltip />
        <Line type="monotone" dataKey="duplicates" />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default DuplicateTrendChart;