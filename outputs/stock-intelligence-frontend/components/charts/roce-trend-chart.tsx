import type { ChartProps, FinancialTrendPoint } from "@/components/charts/chart-types";
import { PlotlyChart } from "@/components/charts/plotly-chart";

export function RoceTrendChart({ data, className = "h-[320px]" }: ChartProps<FinancialTrendPoint>) {
  return (
    <PlotlyChart
      className={className}
      data={[
        {
          x: data.map((item) => item.period),
          y: data.map((item) => item.roce),
          type: "scatter",
          mode: "lines+markers",
          name: "ROCE",
          line: { color: "#4aa3ff", width: 3 },
          marker: { color: "#4aa3ff", size: 7 }
        },
        {
          x: data.map((item) => item.period),
          y: data.map(() => 18),
          type: "scatter",
          mode: "lines",
          name: "18% hurdle",
          line: { color: "#6f7f95", dash: "dot", width: 2 }
        }
      ]}
      layout={{
        title: { text: "ROCE Trend", font: { size: 13 } },
        yaxis: { title: { text: "ROCE (%)" }, gridcolor: "#223042" }
      }}
    />
  );
}
