import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface TrendItem {
  name: string;
  duplicates: number;
}

interface Props {
  data: TrendItem[];
}

const DuplicateTrendChart = ({
  data,
}: Props) => {
  if (!data || data.length === 0) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          color: "#777",
        }}
      >
        No scan data is available for this period.
      </div>
    );
  }

  return (
    <ResponsiveContainer
      width="100%"
      height="100%"
    >
      <LineChart
        data={data}
        margin={{
          top: 10,
          right: 20,
          left: 0,
          bottom: 10,
        }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
        />

        <XAxis
          dataKey="name"
          tick={{
            fontSize: 12,
          }}
        />

        <YAxis
          allowDecimals={false}
          tick={{
            fontSize: 12,
          }}
        />

        <Tooltip />

        <Line
          type="monotone"
          dataKey="duplicates"
          name="Duplicate Groups"
          stroke="#1976d2"
          strokeWidth={3}
          dot={{
            r: 4,
          }}
          activeDot={{
            r: 6,
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default DuplicateTrendChart;