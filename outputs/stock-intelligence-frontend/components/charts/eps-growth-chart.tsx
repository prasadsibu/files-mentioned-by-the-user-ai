import type { ChartProps, FinancialTrendPoint } from "@/components/charts/chart-types";
import { PlotlyChart } from "@/components/charts/plotly-chart";

export function EpsGrowthChart({ data, className = "h-[320px]" }: ChartProps<FinancialTrendPoint>) {
  return (
    <PlotlyChart
      className={className}
      data={[
        {
          x: data.map((item) => item.period),
          y: data.map((item) => item.eps),
          type: "scatter",
          mode: "lines+markers",
          name: "EPS",
          line: { color: "#f5a524", width: 3 },
          marker: { color: "#f5a524", size: 7 }
        }
      ]}
      layout={{
        title: { text: "EPS Growth", font: { size: 13 } },
        yaxis: { title: { text: "EPS (₹)" }, gridcolor: "#223042" }
      }}
    />
  );
}
