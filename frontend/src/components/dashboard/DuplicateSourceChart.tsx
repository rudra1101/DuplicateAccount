import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

interface SourceData {
  name: string;
  value: number;
}

interface Props {
  data: SourceData[];
}

const COLORS = [
  "#1976d2",
  "#2e7d32",
  "#ed6c02",
  "#9c27b0",
  "#d32f2f",
  "#0288d1",
];

const DuplicateSourceChart = ({
  data,
}: Props) => {
  if (!data || data.length === 0) {
    return (
      <div
        style={{
          width: "100%",
          textAlign: "center",
          color: "#777",
        }}
      >
        No source distribution data
        available.
      </div>
    );
  }

  return (
    <ResponsiveContainer
      width="100%"
      height="100%"
    >
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="43%"
          outerRadius={95}
          innerRadius={50}
          paddingAngle={3}
          label={({ percent }) =>
            `${(
              (percent ?? 0) * 100
            ).toFixed(0)}%`
          }
        >
          {data.map(
            (entry, index) => (
              <Cell
                key={`${entry.name}-${index}`}
                fill={
                  COLORS[
                    index %
                      COLORS.length
                  ]
                }
              />
            )
          )}
        </Pie>

        <Tooltip
          formatter={(value) => [
            Number(
              value
            ).toLocaleString(),
            "Duplicate Accounts",
          ]}
        />

        <Legend
          verticalAlign="bottom"
          height={48}
        />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default DuplicateSourceChart;