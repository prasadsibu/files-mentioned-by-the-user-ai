"use client";

import dynamic from "next/dynamic";
import type { Config, Data, Layout } from "plotly.js";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

type PlotlyChartProps = {
  data: Data[];
  layout: Partial<Layout>;
  className?: string;
  darkMode?: boolean;
};

const defaultConfig: Partial<Config> = {
  displayModeBar: false,
  responsive: true
};

export function PlotlyChart({ data, layout, className, darkMode = true }: PlotlyChartProps) {
  const palette = darkMode
    ? {
        paper: "rgba(0,0,0,0)",
        plot: "rgba(0,0,0,0)",
        font: "#c7d2e1",
        grid: "#223042",
        zero: "#223042"
      }
    : {
        paper: "rgba(255,255,255,0)",
        plot: "rgba(255,255,255,0)",
        font: "#172033",
        grid: "#dbe4ef",
        zero: "#dbe4ef"
      };

  return (
    <div className={className}>
      <Plot
        data={data}
        layout={{
          autosize: true,
          paper_bgcolor: palette.paper,
          plot_bgcolor: palette.plot,
          font: { color: palette.font, family: "Inter, sans-serif", size: 11 },
          margin: { l: 42, r: 18, t: 36, b: 34 },
          xaxis: { gridcolor: palette.grid, zerolinecolor: palette.zero },
          yaxis: { gridcolor: palette.grid, zerolinecolor: palette.zero },
          legend: { orientation: "h", y: -0.26 },
          ...layout
        }}
        config={defaultConfig}
        style={{ width: "100%", height: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
