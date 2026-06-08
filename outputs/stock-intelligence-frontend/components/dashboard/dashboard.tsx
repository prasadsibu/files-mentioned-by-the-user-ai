"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Brain,
  Newspaper,
  Radar,
  Search,
  ShieldCheck,
  TrendingUp
} from "lucide-react";

import { analyzeStock } from "@/lib/api";
import {
  defaultScores,
  fundamentalMetrics,
  newsItems,
  riskItems,
  shareholdingData,
  trendData,
  valuationMetrics
} from "@/lib/mock-data";
import type { AnalyzeResponse, Metric, ScoreItem } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  EpsGrowthChart,
  PeComparisonChart,
  PriceTrendChart,
  ProfitGrowthChart,
  RevenueGrowthChart,
  RoceTrendChart,
  RoeTrendChart,
  ShareholdingTrendChart
} from "@/components/charts";

const fallbackResult: AnalyzeResponse = {
  recommendation: "BUY",
  score: 90
};

export function Dashboard() {
  const [stock, setStock] = useState("VOLTAMP");
  const [result, setResult] = useState<AnalyzeResponse>(fallbackResult);
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState<"live" | "sample" | "error">("sample");
  const [error, setError] = useState<string | null>(null);

  const scores = useMemo(() => syncScoresToResult(defaultScores, result), [result]);

  async function onAnalyze() {
    setLoading(true);
    setError(null);

    try {
      const response = await analyzeStock(stock);
      setResult(response);
      setApiStatus("live");
    } catch (err) {
      setResult(fallbackResult);
      setApiStatus("error");
      setError(err instanceof Error ? err.message : "Backend unavailable. Showing sample dashboard.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="market-grid min-h-screen px-3 py-3 sm:px-5 lg:px-6">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-4">
        <TopBar apiStatus={apiStatus} />
        <section className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="flex flex-col gap-4">
            <SearchPanel stock={stock} setStock={setStock} onAnalyze={onAnalyze} loading={loading} error={error} />
            <RecommendationCard stock={stock} result={result} />
            <ScoreBreakdown scores={scores} />
          </aside>

          <section className="grid gap-4">
            <MarketSnapshot />
            <ChartsPanel />
            <section className="grid gap-4 lg:grid-cols-2">
              <MetricsPanel title="Fundamental Metrics" icon={Activity} metrics={fundamentalMetrics} />
              <MetricsPanel title="Valuation Metrics" icon={BarChart3} metrics={valuationMetrics} />
            </section>
            <section className="grid gap-4 lg:grid-cols-[1fr_1fr_1fr]">
              <RiskPanel />
              <NewsPanel />
              <ConcallPanel />
            </section>
          </section>
        </section>
      </div>
    </main>
  );
}

function TopBar({ apiStatus }: { apiStatus: "live" | "sample" | "error" }) {
  const statusVariant = apiStatus === "live" ? "positive" : apiStatus === "error" ? "warning" : "neutral";
  const statusText = apiStatus === "live" ? "FASTAPI LIVE" : apiStatus === "error" ? "SAMPLE FALLBACK" : "LOCAL SAMPLE";

  return (
    <header className="flex flex-col gap-3 rounded-lg border border-border bg-card/80 px-4 py-3 shadow-terminal backdrop-blur md:flex-row md:items-center md:justify-between">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md border border-primary/30 bg-primary/10 text-primary">
          <TrendingUp className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-base font-semibold sm:text-lg">AI Stock Intelligence Terminal</h1>
          <p className="text-xs text-muted-foreground">Indian equities | fundamentals | valuation | sentiment | risk</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Badge variant={statusVariant}>{statusText}</Badge>
        <Badge variant="neutral">NSE / BSE</Badge>
        <Badge variant="neutral">LOCAL FIRST</Badge>
      </div>
    </header>
  );
}

function SearchPanel({
  stock,
  setStock,
  onAnalyze,
  loading,
  error
}: {
  stock: string;
  setStock: (stock: string) => void;
  onAnalyze: () => void;
  loading: boolean;
  error: string | null;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-4 w-4 text-primary" />
          Search Stock
        </CardTitle>
        <CardDescription>Enter an Indian stock symbol and run the scoring engine.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Input
            value={stock}
            onChange={(event) => setStock(event.target.value.toUpperCase())}
            onKeyDown={(event) => {
              if (event.key === "Enter") onAnalyze();
            }}
            placeholder="VOLTAMP"
            className="font-mono"
          />
          <Button onClick={onAnalyze} disabled={loading || !stock.trim()}>
            {loading ? "Analyzing" : "Analyze"}
          </Button>
        </div>
        {error ? (
          <div className="rounded-md border border-terminal-amber/30 bg-terminal-amber/10 px-3 py-2 text-xs text-terminal-amber">
            {error}
          </div>
        ) : null}
        <div className="grid grid-cols-3 gap-2 text-xs">
          {["VOLTAMP", "TCS", "HDFCBANK"].map((symbol) => (
            <button
              key={symbol}
              type="button"
              onClick={() => setStock(symbol)}
              className="rounded-md border border-border bg-secondary/40 px-2 py-2 font-mono text-muted-foreground transition-colors hover:text-foreground"
            >
              {symbol}
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function RecommendationCard({ stock, result }: { stock: string; result: AnalyzeResponse }) {
  const tone = result.recommendation === "BUY" ? "positive" : result.recommendation === "WATCH" ? "warning" : "negative";
  const scoreColor =
    result.score >= 80 ? "text-terminal-green" : result.score >= 60 ? "text-terminal-amber" : "text-terminal-red";

  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b border-border bg-secondary/25">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-mono text-lg">{stock || "VOLTAMP"}</CardTitle>
            <CardDescription>Recommendation Summary</CardDescription>
          </div>
          <Badge variant={tone}>{result.recommendation}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 pt-4">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs uppercase text-muted-foreground">Overall Score</p>
            <p className={cn("font-mono text-6xl font-semibold leading-none", scoreColor)}>{result.score}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Confidence</p>
            <p className="font-mono text-lg text-foreground">{result.score >= 80 ? "HIGH" : "MEDIUM"}</p>
          </div>
        </div>
        <Progress
          value={result.score}
          indicatorClassName={cn(
            result.score >= 80 && "bg-terminal-green",
            result.score >= 60 && result.score < 80 && "bg-terminal-amber",
            result.score < 60 && "bg-terminal-red"
          )}
        />
        <p className="text-sm leading-6 text-muted-foreground">
          The engine favors quality, growth, valuation discipline, ownership strength, sentiment, concall signals, and
          risk penalties. Every category contributes to the final 100-point score.
        </p>
      </CardContent>
    </Card>
  );
}

function ScoreBreakdown({ scores }: { scores: ScoreItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Radar className="h-4 w-4 text-primary" />
          Score Breakdown
        </CardTitle>
        <CardDescription>Weighted scoring model out of 100.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {scores.map((item) => (
          <div key={item.label} className="space-y-1.5 rounded-md border border-border bg-secondary/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium">{item.label}</p>
                <p className="text-xs text-muted-foreground">Weight {item.weight}</p>
              </div>
              <Badge variant={item.status === "positive" ? "positive" : item.status === "negative" ? "negative" : "neutral"}>
                {item.score}/100
              </Badge>
            </div>
            <Progress value={item.score} indicatorClassName={item.status === "positive" ? "bg-terminal-green" : "bg-primary"} />
            <p className="text-xs leading-5 text-muted-foreground">{item.reason}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function MarketSnapshot() {
  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {[
        ["Revenue CAGR", "25.5%", "+10.5 pp vs hurdle", "positive"],
        ["Profit CAGR", "34.5%", "+14.5 pp vs hurdle", "positive"],
        ["PE Discount", "34.4%", "vs industry PE", "positive"],
        ["Risk Flags", "0", "critical flags detected", "neutral"]
      ].map(([label, value, delta, tone]) => (
        <Card key={label}>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{label}</p>
            <div className="mt-2 flex items-end justify-between gap-3">
              <p className="font-mono text-2xl font-semibold">{value}</p>
              <Badge variant={tone === "positive" ? "positive" : "neutral"}>{delta}</Badge>
            </div>
          </CardContent>
        </Card>
      ))}
    </section>
  );
}

function MetricsPanel({ title, icon: Icon, metrics }: { title: string; icon: typeof Activity; metrics: Metric[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <table className="metric-table w-full text-sm">
          <tbody>
            {metrics.map((metric) => (
              <tr key={metric.label}>
                <td className="py-2 text-muted-foreground">{metric.label}</td>
                <td className="py-2 text-right font-mono text-foreground">{metric.value}</td>
                <td
                  className={cn(
                    "hidden py-2 text-right text-xs sm:table-cell",
                    metric.tone === "positive" && "text-terminal-green",
                    metric.tone === "negative" && "text-terminal-red",
                    (!metric.tone || metric.tone === "neutral") && "text-muted-foreground"
                  )}
                >
                  {metric.delta ?? "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function ChartsPanel() {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-primary" />
            Interactive Charts
          </CardTitle>
          <CardDescription>Plotly charts for growth, valuation, price, and ownership trends.</CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="growth">
          <TabsList className="mb-4 flex w-full overflow-x-auto sm:w-auto">
            <TabsTrigger value="growth">Growth</TabsTrigger>
            <TabsTrigger value="quality">Quality</TabsTrigger>
            <TabsTrigger value="valuation">Valuation</TabsTrigger>
            <TabsTrigger value="ownership">Ownership</TabsTrigger>
            <TabsTrigger value="price">Price</TabsTrigger>
          </TabsList>
          <TabsContent value="growth">
            <div className="grid gap-4 xl:grid-cols-3">
              <RevenueGrowthChart data={trendData} className="h-[320px]" />
              <ProfitGrowthChart data={trendData} className="h-[320px]" />
              <EpsGrowthChart data={trendData} className="h-[320px]" />
            </div>
          </TabsContent>
          <TabsContent value="quality">
            <div className="grid gap-4 xl:grid-cols-2">
              <RoeTrendChart data={trendData} className="h-[340px]" />
              <RoceTrendChart data={trendData} className="h-[340px]" />
            </div>
          </TabsContent>
          <TabsContent value="valuation">
            <PeComparisonChart data={trendData} industryPe={32} className="h-[360px]" />
          </TabsContent>
          <TabsContent value="ownership">
            <ShareholdingTrendChart data={shareholdingData} className="h-[360px]" />
          </TabsContent>
          <TabsContent value="price">
            <PriceTrendChart data={trendData} className="h-[360px]" />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function RiskPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Risk Metrics
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {riskItems.map((item) => (
          <div key={item.label} className="rounded-md border border-border bg-secondary/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium">{item.label}</p>
              <Badge variant={item.detected ? "negative" : "positive"}>{item.detected ? item.severity : "Clear"}</Badge>
            </div>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.detail}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function NewsPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Newspaper className="h-4 w-4 text-primary" />
          News Analysis
        </CardTitle>
        <CardDescription>FinBERT-ready sentiment surface.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {newsItems.map((item) => (
          <div key={item.title} className="rounded-md border border-border bg-secondary/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <Badge variant={item.sentiment === "Positive" ? "positive" : item.sentiment === "Negative" ? "negative" : "neutral"}>
                {item.sentiment}
              </Badge>
              <span className="font-mono text-xs text-muted-foreground">{item.score.toFixed(2)}</span>
            </div>
            <p className="mt-2 text-sm leading-5">{item.title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{item.source}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ConcallPanel() {
  const signals = [
    ["Expansion plans", "Capacity expansion commentary detected", "positive"],
    ["Order book", "Demand outlook remains constructive", "positive"],
    ["Margins", "Input volatility noted but manageable", "neutral"],
    ["Debt commentary", "No major debt concern", "positive"]
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-primary" />
          Concall Analysis
        </CardTitle>
        <CardDescription>Transcript evidence and management signal extraction.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {signals.map(([label, detail, tone]) => (
          <div key={label} className="rounded-md border border-border bg-secondary/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium">{label}</p>
              <Badge variant={tone === "positive" ? "positive" : "neutral"}>{tone}</Badge>
            </div>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
          </div>
        ))}
        <div className="rounded-md border border-primary/25 bg-primary/10 p-3 text-xs leading-5 text-primary">
          AI summary: management tone appears constructive, backed by capex cycle demand and clean balance sheet.
        </div>
      </CardContent>
    </Card>
  );
}

function syncScoresToResult(scores: ScoreItem[], result: AnalyzeResponse): ScoreItem[] {
  const baseWeighted = scores.reduce((sum, item) => sum + (item.score * item.weight) / 100, 0);
  if (Math.round(baseWeighted) === result.score) return scores;

  return scores.map((item) =>
    item.label === "News Sentiment" || item.label === "Concall"
      ? {
          ...item,
          reason: "Neutral placeholder. Backend returned the final recommendation score; richer category API can replace this."
        }
      : item
  );
}
