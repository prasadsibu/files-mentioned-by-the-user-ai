import type { ChartProps, FinancialTrendPoint } from "@/components/charts/chart-types";
import { PlotlyChart } from "@/components/charts/plotly-chart";

export function RevenueGrowthChart({ data, className = "h-[320px]" }: ChartProps<FinancialTrendPoint>) {
  return (
    <PlotlyChart
      className={className}
      data={[
        {
          x: data.map((item) => item.period),
          y: data.map((item) => item.revenue),
          type: "scatter",
          mode: "lines+markers",
          name: "Revenue",
          fill: "tozeroy",
          line: { color: "#4aa3ff", width: 3 },
          marker: { color: "#4aa3ff", size: 7 }
        }
      ]}
      layout={{
        title: { text: "Revenue Growth", font: { size: 13 } },
        yaxis: { title: "Revenue (₹ Cr)", gridcolor: "#223042" }
      }}
    />
  );
}
