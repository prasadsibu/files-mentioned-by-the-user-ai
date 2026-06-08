import type { ChartProps, ShareholdingTrendPoint } from "@/components/charts/chart-types";
import { PlotlyChart } from "@/components/charts/plotly-chart";

export function ShareholdingTrendChart({ data, className = "h-[320px]" }: ChartProps<ShareholdingTrendPoint>) {
  const quarters = data.map((item) => item.quarter);

  return (
    <PlotlyChart
      className={className}
      data={[
        { x: quarters, y: data.map((item) => item.promoter), type: "scatter", mode: "lines+markers", name: "Promoter", line: { color: "#4aa3ff", width: 3 } },
        { x: quarters, y: data.map((item) => item.fii), type: "scatter", mode: "lines+markers", name: "FII", line: { color: "#16c784", width: 3 } },
        { x: quarters, y: data.map((item) => item.dii), type: "scatter", mode: "lines+markers", name: "DII", line: { color: "#f5a524", width: 3 } },
        { x: quarters, y: data.map((item) => item.retail), type: "scatter", mode: "lines+markers", name: "Retail", line: { color: "#ea3943", width: 3 } }
      ]}
      layout={{
        title: { text: "Shareholding Trend", font: { size: 13 } },
        yaxis: { title: { text: "Holding (%)" }, gridcolor: "#223042" }
      }}
    />
  );
}
