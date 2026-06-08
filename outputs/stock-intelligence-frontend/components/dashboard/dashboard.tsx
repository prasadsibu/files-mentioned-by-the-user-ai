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
import type { AnalyzeResponse, Metric, NewsItem, RiskItem, ScoreItem, ShareholdingPoint, TrendPoint } from "@/lib/types";
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

const suggestedSymbols = ["TCS", "RELIANCE", "INFY", "HDFCBANK", "ICICIBANK", "LT", "TITAN"];

export function Dashboard() {
  const [stock, setStock] = useState("TCS");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState<"idle" | "live" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [concallTranscript, setConcallTranscript] = useState("");
  const [concallTranscriptUrl, setConcallTranscriptUrl] = useState("");

  const scores = useMemo(() => toScoreItems(result), [result]);
  const fundamentalMetrics = useMemo(() => toFundamentalMetrics(result), [result]);
  const valuationMetrics = useMemo(() => toValuationMetrics(result), [result]);
  const trendHistory = result?.trend_history ?? [];
  const shareholdingHistory = result?.shareholding_history ?? [];
  const riskFlags = result?.risk_flags ?? [];
  const newsItems = result?.news_sentiment.articles ?? [];

  async function onAnalyze(nextStock = stock) {
    const symbol = nextStock.trim().toUpperCase();
    if (!symbol) return;
    setStock(symbol);
    setLoading(true);
    setError(null);

    try {
      const response = await analyzeStock(symbol, {
        concallTranscript: concallTranscript.trim() || undefined,
        concallTranscriptUrl: concallTranscriptUrl.trim() || undefined
      });
      setResult(response);
      setApiStatus("live");
    } catch (err) {
      setApiStatus("error");
      setError(err instanceof Error ? err.message : "Backend unavailable. Please try again.");
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
            <SearchPanel
              stock={stock}
              setStock={setStock}
              onAnalyze={onAnalyze}
              loading={loading}
              error={error}
              concallTranscript={concallTranscript}
              setConcallTranscript={setConcallTranscript}
              concallTranscriptUrl={concallTranscriptUrl}
              setConcallTranscriptUrl={setConcallTranscriptUrl}
            />
            <RecommendationCard stock={stock} result={result} />
            <ScoreBreakdown scores={scores} />
          </aside>

          <section className="grid gap-4">
            <MarketSnapshot result={result} />
            <ChartsPanel trendHistory={trendHistory} shareholdingHistory={shareholdingHistory} industryPe={result?.valuation.industry_pe ?? 0} />
            <section className="grid gap-4 lg:grid-cols-2">
              <MetricsPanel title="Fundamental Metrics" icon={Activity} metrics={fundamentalMetrics} />
              <MetricsPanel title="Valuation Metrics" icon={BarChart3} metrics={valuationMetrics} />
            </section>
            <section className="grid gap-4 lg:grid-cols-[1fr_1fr_1fr]">
              <RiskPanel risks={riskFlags} />
              <NewsPanel sentiment={result?.news_sentiment ?? null} newsItems={newsItems} />
              <ConcallPanel summary={result?.concall_summary ?? null} />
            </section>
          </section>
        </section>
      </div>
    </main>
  );
}

function TopBar({ apiStatus }: { apiStatus: "idle" | "live" | "error" }) {
  const statusVariant = apiStatus === "live" ? "positive" : apiStatus === "error" ? "warning" : "neutral";
  const statusText = apiStatus === "live" ? "FASTAPI LIVE" : apiStatus === "error" ? "API ERROR" : "READY";

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
        <Badge variant="neutral">API DATA</Badge>
      </div>
    </header>
  );
}

function SearchPanel({
  stock,
  setStock,
  onAnalyze,
  loading,
  error,
  concallTranscript,
  setConcallTranscript,
  concallTranscriptUrl,
  setConcallTranscriptUrl
}: {
  stock: string;
  setStock: (stock: string) => void;
  onAnalyze: (stock?: string) => void;
  loading: boolean;
  error: string | null;
  concallTranscript: string;
  setConcallTranscript: (value: string) => void;
  concallTranscriptUrl: string;
  setConcallTranscriptUrl: (value: string) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-4 w-4 text-primary" />
          Search Stock
        </CardTitle>
        <CardDescription>Enter an NSE stock symbol and run the scoring engine.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Input
            value={stock}
            onChange={(event) => setStock(event.target.value.toUpperCase())}
            onKeyDown={(event) => {
              if (event.key === "Enter") onAnalyze();
            }}
            placeholder="TCS"
            className="font-mono"
          />
          <Button onClick={() => onAnalyze()} disabled={loading || !stock.trim()}>
            {loading ? "Analyzing" : "Analyze"}
          </Button>
        </div>
        {error ? (
          <div className="rounded-md border border-terminal-amber/30 bg-terminal-amber/10 px-3 py-2 text-xs text-terminal-amber">
            {error}
          </div>
        ) : null}

        <div className="space-y-2 rounded-md border border-border bg-secondary/20 p-3">
          <p className="text-xs font-medium text-muted-foreground">Optional concall transcript intelligence</p>
          <Input
            value={concallTranscriptUrl}
            onChange={(event) => setConcallTranscriptUrl(event.target.value)}
            placeholder="Transcript URL"
            className="font-mono text-xs"
          />
          <textarea
            value={concallTranscript}
            onChange={(event) => setConcallTranscript(event.target.value)}
            placeholder="Paste transcript text, or upload a .txt file below"
            className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-xs text-foreground shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
          <input
            type="file"
            accept=".txt,text/plain"
            className="block w-full text-xs text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-primary/10 file:px-3 file:py-1.5 file:text-xs file:text-primary"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              void file.text().then(setConcallTranscript);
            }}
          />
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
          {suggestedSymbols.map((symbol) => (
            <button
              key={symbol}
              type="button"
              onClick={() => onAnalyze(symbol)}
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

function RecommendationCard({ stock, result }: { stock: string; result: AnalyzeResponse | null }) {
  const recommendation = result?.recommendation ?? "WATCH";
  const score = result?.score ?? 0;
  const tone = recommendation === "BUY" ? "positive" : recommendation === "WATCH" ? "warning" : "negative";
  const scoreColor = score >= 80 ? "text-terminal-green" : score >= 60 ? "text-terminal-amber" : "text-terminal-red";

  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b border-border bg-secondary/25">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-mono text-lg">{result?.symbol || stock || "Select symbol"}</CardTitle>
            <CardDescription>Recommendation Summary</CardDescription>
          </div>
          <Badge variant={result ? tone : "neutral"}>{result ? recommendation : "Pending"}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 pt-4">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs uppercase text-muted-foreground">Overall Score</p>
            <p className={cn("font-mono text-6xl font-semibold leading-none", result ? scoreColor : "text-muted-foreground")}>{result ? score : "--"}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Confidence</p>
            <p className="font-mono text-lg text-foreground">{result ? (score >= 80 ? "HIGH" : score >= 60 ? "MEDIUM" : "LOW") : "--"}</p>
          </div>
        </div>
        <Progress
          value={score}
          indicatorClassName={cn(
            score >= 80 && "bg-terminal-green",
            score >= 60 && score < 80 && "bg-terminal-amber",
            score < 60 && "bg-terminal-red"
          )}
        />
        <p className="text-sm leading-6 text-muted-foreground">
          {result
            ? `This dashboard is bound to the latest /analyze payload for ${result.symbol}.`
            : "Run an analysis to load fundamentals, charts, ownership, news, concall, and risk data from the API."}
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
        {scores.length ? (
          scores.map((item) => (
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
              <Progress value={item.score} indicatorClassName={item.status === "positive" ? "bg-terminal-green" : item.status === "negative" ? "bg-terminal-red" : "bg-primary"} />
              <p className="text-xs leading-5 text-muted-foreground">{item.reason}</p>
            </div>
          ))
        ) : (
          <EmptyState message="Score breakdown will appear after analysis." />
        )}
      </CardContent>
    </Card>
  );
}

function MarketSnapshot({ result }: { result: AnalyzeResponse | null }) {
  const trend = result?.trend_history ?? [];
  const first = trend[0];
  const latest = trend[trend.length - 1];
  const revenueCagr = first && latest ? cagr(first.revenue, latest.revenue, Math.max(trend.length - 1, 1)) : null;
  const profitCagr = first && latest ? cagr(first.profit, latest.profit, Math.max(trend.length - 1, 1)) : null;
  const peDiscount = result ? ((result.valuation.industry_pe - result.valuation.pe) / Math.max(result.valuation.industry_pe, 1)) * 100 : null;
  const riskCount = result?.risk_flags.filter((item) => item.detected).length ?? null;

  const items = [
    ["Revenue CAGR", percentOrDash(revenueCagr), revenueCagr === null ? "Run analysis" : "from API history", revenueCagr !== null && revenueCagr > 15 ? "positive" : "neutral"],
    ["Profit CAGR", percentOrDash(profitCagr), profitCagr === null ? "Run analysis" : "from API history", profitCagr !== null && profitCagr > 20 ? "positive" : "neutral"],
    ["PE Discount", percentOrDash(peDiscount), peDiscount === null ? "Run analysis" : "vs industry PE", peDiscount !== null && peDiscount > 0 ? "positive" : "neutral"],
    ["Risk Flags", riskCount === null ? "--" : String(riskCount), "detected flags", riskCount === 0 ? "positive" : "neutral"]
  ];

  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map(([label, value, delta, tone]) => (
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
        {metrics.length ? (
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
        ) : (
          <EmptyState message="Metrics will appear after analysis." />
        )}
      </CardContent>
    </Card>
  );
}

function ChartsPanel({
  trendHistory,
  shareholdingHistory,
  industryPe
}: {
  trendHistory: TrendPoint[];
  shareholdingHistory: ShareholdingPoint[];
  industryPe: number;
}) {
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
        {trendHistory.length ? (
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
                <RevenueGrowthChart data={trendHistory} className="h-[320px]" />
                <ProfitGrowthChart data={trendHistory} className="h-[320px]" />
                <EpsGrowthChart data={trendHistory} className="h-[320px]" />
              </div>
            </TabsContent>
            <TabsContent value="quality">
              <div className="grid gap-4 xl:grid-cols-2">
                <RoeTrendChart data={trendHistory} className="h-[340px]" />
                <RoceTrendChart data={trendHistory} className="h-[340px]" />
              </div>
            </TabsContent>
            <TabsContent value="valuation">
              <PeComparisonChart data={trendHistory} industryPe={industryPe} className="h-[360px]" />
            </TabsContent>
            <TabsContent value="ownership">
              {shareholdingHistory.length ? (
                <ShareholdingTrendChart data={shareholdingHistory} className="h-[360px]" />
              ) : (
                <EmptyState message="Shareholding history was not returned by the API." />
              )}
            </TabsContent>
            <TabsContent value="price">
              <PriceTrendChart data={trendHistory} className="h-[360px]" />
            </TabsContent>
          </Tabs>
        ) : (
          <EmptyState message="Charts will render after the API returns trend history." />
        )}
      </CardContent>
    </Card>
  );
}

function RiskPanel({ risks }: { risks: RiskItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Risk Metrics
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {risks.length ? (
          risks.map((item) => (
            <div key={item.label} className="rounded-md border border-border bg-secondary/20 p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium">{item.label}</p>
                <Badge variant={item.detected ? "negative" : "positive"}>{item.detected ? item.severity : "Clear"}</Badge>
              </div>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.detail}</p>
            </div>
          ))
        ) : (
          <EmptyState message="Risk flags will appear after analysis." />
        )}
      </CardContent>
    </Card>
  );
}

function NewsPanel({ sentiment, newsItems }: { sentiment: AnalyzeResponse["news_sentiment"] | null; newsItems: NewsItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Newspaper className="h-4 w-4 text-primary" />
          News Analysis
        </CardTitle>
        <CardDescription>
          {sentiment ? `Sentiment score ${sentiment.sentiment_score}/100 · +${sentiment.positive}% / ${sentiment.neutral}% / -${sentiment.negative}%` : "Awaiting API sentiment payload."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {newsItems.length ? (
          newsItems.map((item) => (
            <div key={`${item.source}-${item.title}`} className="rounded-md border border-border bg-secondary/20 p-3">
              <div className="flex items-center justify-between gap-3">
                <Badge variant={item.sentiment === "Positive" ? "positive" : item.sentiment === "Negative" ? "negative" : "neutral"}>
                  {item.sentiment}
                </Badge>
                <span className="font-mono text-xs text-muted-foreground">{item.score.toFixed(2)}</span>
              </div>
              <a className="mt-2 block text-sm leading-5 hover:text-primary" href={item.url} target="_blank" rel="noreferrer">{item.title}</a>
              <p className="mt-1 text-xs text-muted-foreground">{item.source}{item.published_at ? ` · ${new Date(item.published_at).toLocaleDateString("en-IN")}` : ""}</p>
            </div>
          ))
        ) : (
          <EmptyState message="News sentiment will appear after analysis." />
        )}
      </CardContent>
    </Card>
  );
}

function ConcallPanel({ summary }: { summary: AnalyzeResponse["concall_summary"] | null }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-primary" />
          Concall Analysis
        </CardTitle>
        <CardDescription>
          {summary ? `${summary.final_view} view · ${summary.confidence}% confidence` : "Awaiting API concall payload."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {summary ? (
          <>
            {summary.signals.map((signal) => (
              <div key={signal.label} className="rounded-md border border-border bg-secondary/20 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium">{signal.label}</p>
                  <Badge variant={signal.tone === "positive" ? "positive" : signal.tone === "negative" ? "negative" : "neutral"}>{signal.tone}</Badge>
                </div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{signal.detail}</p>
              </div>
            ))}
            <div className="rounded-md border border-primary/25 bg-primary/10 p-3 text-xs leading-5 text-primary">
              AI summary: {summary.reasoning}
            </div>
          </>
        ) : (
          <EmptyState message="Concall summary will appear after analysis." />
        )}
      </CardContent>
    </Card>
  );
}

function EmptyState({ message }: { message: string }) {
  return <div className="rounded-md border border-dashed border-border bg-secondary/10 p-4 text-sm text-muted-foreground">{message}</div>;
}

function toScoreItems(result: AnalyzeResponse | null): ScoreItem[] {
  if (!result) return [];
  return result.score_breakdown.map((item) => ({
    label: titleCase(item.category),
    score: item.score,
    weight: item.weight,
    status: item.score >= 70 ? "positive" : item.score >= 45 ? "neutral" : "negative",
    reason: item.reasoning
  }));
}

function toFundamentalMetrics(result: AnalyzeResponse | null): Metric[] {
  if (!result) return [];
  const latest = result.trend_history[result.trend_history.length - 1];
  const previous = result.trend_history[result.trend_history.length - 2];
  const fundamentals = result.fundamentals;
  return [
    { label: "ROE", value: formatPercent(fundamentals.roe), delta: deltaPercent(latest?.roe, previous?.roe), tone: fundamentals.roe >= 15 ? "positive" : "neutral" },
    { label: "ROCE", value: formatPercent(fundamentals.roce), delta: deltaPercent(latest?.roce, previous?.roce), tone: fundamentals.roce >= 18 ? "positive" : "neutral" },
    { label: "Debt / Equity", value: `${formatNumber(fundamentals.debt_equity)}x`, delta: fundamentals.debt_equity <= 0.5 ? "conservative" : "elevated", tone: fundamentals.debt_equity <= 0.5 ? "positive" : "negative" },
    { label: "Operating Cash Flow", value: formatCurrencyCr(fundamentals.operating_cash_flow), delta: deltaGrowth(latest?.profit, previous?.profit), tone: fundamentals.operating_cash_flow > 0 ? "positive" : "negative" },
    { label: "Free Cash Flow", value: formatCurrencyCr(fundamentals.free_cash_flow), delta: fundamentals.free_cash_flow >= 0 ? "positive" : "negative", tone: fundamentals.free_cash_flow >= 0 ? "positive" : "negative" },
    { label: "EPS", value: `₹${formatNumber(fundamentals.eps)}`, delta: deltaGrowth(latest?.eps, previous?.eps), tone: fundamentals.eps > 0 ? "positive" : "negative" }
  ];
}

function toValuationMetrics(result: AnalyzeResponse | null): Metric[] {
  if (!result) return [];
  const valuation = result.valuation;
  const peDiscount = ((valuation.industry_pe - valuation.pe) / Math.max(valuation.industry_pe, 1)) * 100;
  return [
    { label: "Current PE", value: `${formatNumber(valuation.pe)}x`, delta: `vs ${formatNumber(valuation.industry_pe)}x industry`, tone: valuation.pe < valuation.industry_pe ? "positive" : "negative" },
    { label: "PB", value: `${formatNumber(valuation.pb)}x`, delta: valuation.pb <= 4 ? "reasonable" : "premium", tone: valuation.pb <= 4 ? "positive" : "neutral" },
    { label: "PEG", value: `${formatNumber(valuation.peg)}x`, delta: valuation.peg <= 1 ? "below 1" : "above 1", tone: valuation.peg <= 1 ? "positive" : "neutral" },
    { label: "Industry PE", value: `${formatNumber(valuation.industry_pe)}x`, tone: "neutral" },
    { label: "Price", value: `₹${formatNumber(valuation.price)}`, delta: "latest close", tone: "neutral" },
    { label: "PE Discount", value: formatPercent(peDiscount), delta: "vs industry", tone: peDiscount > 0 ? "positive" : "negative" }
  ];
}

function cagr(start: number, end: number, years: number) {
  if (start <= 0 || end <= 0) return 0;
  return ((end / start) ** (1 / years) - 1) * 100;
}

function deltaGrowth(current?: number, previous?: number) {
  if (current === undefined || previous === undefined || previous === 0) return "-";
  return `${current >= previous ? "+" : ""}${formatPercent(((current - previous) / Math.abs(previous)) * 100)}`;
}

function deltaPercent(current?: number, previous?: number) {
  if (current === undefined || previous === undefined) return "-";
  const delta = current - previous;
  return `${delta >= 0 ? "+" : ""}${formatNumber(delta)} pp`;
}

function percentOrDash(value: number | null) {
  return value === null ? "--" : formatPercent(value);
}

function formatPercent(value: number) {
  return `${formatNumber(value)}%`;
}

function formatCurrencyCr(value: number) {
  return `₹${formatNumber(value)} Cr`;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(value);
}

function titleCase(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\w\S*/g, (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
}
