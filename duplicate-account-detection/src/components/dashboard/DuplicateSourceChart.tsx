import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const data = [
  { name: "Active Directory", value: 78 },
  { name: "Entra ID", value: 42 },
  { name: "ServiceNow", value: 26 },
  { name: "SAP", value: 18 },
  { name: "Salesforce", value: 12 },
];

const COLORS = [
  "#1976d2",
  "#2e7d32",
  "#ed6c02",
  "#d32f2f",
  "#7b1fa2",
];

const DuplicateSourceChart = () => {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={70}
          outerRadius={110}
          paddingAngle={2}
          label
        >
          {data.map((_, index) => (
            <Cell
              key={index}
              fill={COLORS[index]}
            />
          ))}
        </Pie>

        <Tooltip />

        <Legend verticalAlign="bottom" />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default DuplicateSourceChart;