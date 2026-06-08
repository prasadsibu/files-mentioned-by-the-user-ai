import type { ChartProps, FinancialTrendPoint } from "@/components/charts/chart-types";
import { PlotlyChart } from "@/components/charts/plotly-chart";

export function RoeTrendChart({ data, className = "h-[320px]" }: ChartProps<FinancialTrendPoint>) {
  return (
    <PlotlyChart
      className={className}
      data={[
        {
          x: data.map((item) => item.period),
          y: data.map((item) => item.roe),
          type: "scatter",
          mode: "lines+markers",
          name: "ROE",
          line: { color: "#16c784", width: 3 },
          marker: { color: "#16c784", size: 7 }
        },
        {
          x: data.map((item) => item.period),
          y: data.map(() => 15),
          type: "scatter",
          mode: "lines",
          name: "15% hurdle",
          line: { color: "#6f7f95", dash: "dot", width: 2 }
        }
      ]}
      layout={{
        title: { text: "ROE Trend", font: { size: 13 } },
        yaxis: { title: { text: "ROE (%)" }, gridcolor: "#223042" }
      }}
    />
  );
}
