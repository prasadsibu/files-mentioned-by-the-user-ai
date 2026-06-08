import type { ChartProps, FinancialTrendPoint } from "@/components/charts/chart-types";
import { PlotlyChart } from "@/components/charts/plotly-chart";

type PeComparisonChartProps = ChartProps<FinancialTrendPoint> & {
  industryPe?: number;
};

export function PeComparisonChart({ data, industryPe = 32, className = "h-[320px]" }: PeComparisonChartProps) {
  return (
    <PlotlyChart
      className={className}
      data={[
        {
          x: data.map((item) => item.period),
          y: data.map((item) => item.pe),
          type: "bar",
          name: "Stock PE",
          marker: { color: "#f5a524" }
        },
        {
          x: data.map((item) => item.period),
          y: data.map(() => industryPe),
          type: "scatter",
          mode: "lines",
          name: "Industry PE",
          line: { color: "#4aa3ff", dash: "dash", width: 3 }
        }
      ]}
      layout={{
        title: { text: "PE Comparison", font: { size: 13 } },
        yaxis: { title: { text: "PE Multiple" }, gridcolor: "#223042" }
      }}
    />
  );
}
