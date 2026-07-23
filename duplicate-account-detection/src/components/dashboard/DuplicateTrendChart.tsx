import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

interface TrendData {
  name: string;
  duplicates: number;
}

interface DuplicateTrendChartProps {
  data: TrendData[];
}

const DuplicateTrendChart = ({
  data,
}: DuplicateTrendChartProps) => {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart
        data={data}
        margin={{
          top: 10,
          right: 20,
          left: 0,
          bottom: 0,
        }}
      >
        <CartesianGrid strokeDasharray="4 4" />

        <XAxis dataKey="name" />

        <YAxis allowDecimals={false} />

        <Tooltip />

        <Line
          type="monotone"
          dataKey="duplicates"
          stroke="#1976d2"
          strokeWidth={3}
          dot={{ r: 5 }}
          activeDot={{ r: 8 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default DuplicateTrendChart;