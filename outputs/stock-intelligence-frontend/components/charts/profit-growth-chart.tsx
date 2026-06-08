import type { ChartProps, FinancialTrendPoint } from "@/components/charts/chart-types";
import { PlotlyChart } from "@/components/charts/plotly-chart";

export function ProfitGrowthChart({ data, className = "h-[320px]" }: ChartProps<FinancialTrendPoint>) {
  return (
    <PlotlyChart
      className={className}
      data={[
        {
          x: data.map((item) => item.period),
          y: data.map((item) => item.profit),
          type: "bar",
          name: "Profit",
          marker: { color: "#16c784" }
        }
      ]}
      layout={{
        title: { text: "Profit Growth", font: { size: 13 } },
        yaxis: { title: "Profit (₹ Cr)", gridcolor: "#223042" }
      }}
    />
  );
}
