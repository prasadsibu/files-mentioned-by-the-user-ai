import type { ChartProps, FinancialTrendPoint } from "@/components/charts/chart-types";
import { PlotlyChart } from "@/components/charts/plotly-chart";

export function PriceTrendChart({ data, className = "h-[320px]" }: ChartProps<FinancialTrendPoint>) {
  return (
    <PlotlyChart
      className={className}
      data={[
        {
          x: data.map((item) => item.period),
          y: data.map((item) => item.price),
          type: "scatter",
          mode: "lines+markers",
          name: "Price",
          fill: "tozeroy",
          line: { color: "#16c784", width: 3 },
          marker: { color: "#16c784", size: 7 }
        }
      ]}
      layout={{
        title: { text: "Price Trend", font: { size: 13 } },
        yaxis: { title: "Price (₹)", gridcolor: "#223042" }
      }}
    />
  );
}
