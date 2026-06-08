import type { Metric, NewsItem, RiskItem, ScoreItem, ShareholdingPoint, TrendPoint } from "@/lib/types";

export const defaultScores: ScoreItem[] = [
  { label: "Fundamentals", score: 100, weight: 25, status: "positive", reason: "ROE, ROCE, and leverage clear preferred thresholds." },
  { label: "Growth", score: 100, weight: 20, status: "positive", reason: "Revenue and profit CAGR are compounding above hurdle rates." },
  { label: "Valuation", score: 100, weight: 15, status: "positive", reason: "PE is below industry average with PEG below 1." },
  { label: "Ownership", score: 100, weight: 10, status: "positive", reason: "Promoter holding is above 50%; FII and DII ownership are rising." },
  { label: "News Sentiment", score: 50, weight: 10, status: "neutral", reason: "Neutral placeholder until FinBERT news feed is connected." },
  { label: "Concall", score: 50, weight: 10, status: "neutral", reason: "Neutral placeholder until transcript analysis is connected." },
  { label: "Risk", score: 100, weight: 10, status: "positive", reason: "No pledged shares, dilution, auditor resignation, or negative cash flow detected." }
];

export const fundamentalMetrics: Metric[] = [
  { label: "ROE", value: "24.0%", delta: "+1.0 pp", tone: "positive" },
  { label: "ROCE", value: "31.0%", delta: "+3.0 pp", tone: "positive" },
  { label: "Debt / Equity", value: "0.02x", delta: "-0.01x", tone: "positive" },
  { label: "Operating Cash Flow", value: "₹315 Cr", delta: "+37%", tone: "positive" },
  { label: "Free Cash Flow", value: "₹260 Cr", delta: "+37%", tone: "positive" },
  { label: "EPS", value: "₹275", delta: "+37%", tone: "positive" }
];

export const valuationMetrics: Metric[] = [
  { label: "Current PE", value: "21.0x", delta: "vs 32x industry", tone: "positive" },
  { label: "PB", value: "3.7x", delta: "reasonable", tone: "neutral" },
  { label: "PEG", value: "0.8x", delta: "below 1", tone: "positive" },
  { label: "Industry PE", value: "32.0x", tone: "neutral" },
  { label: "Price", value: "₹9,800", delta: "+18% 1Y", tone: "positive" },
  { label: "Valuation View", value: "Attractive", tone: "positive" }
];

export const trendData: TrendPoint[] = [
  { period: "FY21", revenue: 900, profit: 115, eps: 112, roe: 18, roce: 22, pe: 28, price: 3800 },
  { period: "FY22", revenue: 1120, profit: 150, eps: 146, roe: 20, roce: 24, pe: 25, price: 4700 },
  { period: "FY23", revenue: 1430, profit: 205, eps: 201, roe: 23, roce: 28, pe: 23, price: 6900 },
  { period: "FY24", revenue: 1780, profit: 280, eps: 275, roe: 24, roce: 31, pe: 21, price: 9800 }
];

export const shareholdingData: ShareholdingPoint[] = [
  { quarter: "Q1 FY24", promoter: 50.1, fii: 6.8, dii: 9.4, retail: 33.7 },
  { quarter: "Q2 FY24", promoter: 50.1, fii: 7.1, dii: 10.2, retail: 32.6 },
  { quarter: "Q3 FY24", promoter: 50.1, fii: 7.5, dii: 10.9, retail: 31.5 },
  { quarter: "Q4 FY24", promoter: 50.1, fii: 8.2, dii: 11.7, retail: 30.0 }
];

export const newsItems: NewsItem[] = [
  { title: "Transformer order inflow remains strong across industrial customers", source: "Market Feed", sentiment: "Positive", score: 0.82 },
  { title: "Capital goods pack trades firm as power capex cycle improves", source: "Exchange Desk", sentiment: "Positive", score: 0.76 },
  { title: "Input cost volatility keeps margins under investor watch", source: "Sector Wire", sentiment: "Neutral", score: 0.51 }
];

export const riskItems: RiskItem[] = [
  { label: "Auditor resignation", severity: "High", detected: false, detail: "No recent resignation flag in local records." },
  { label: "Rising debt", severity: "Medium", detected: false, detail: "Debt/equity remains close to zero." },
  { label: "Negative cash flow", severity: "High", detected: false, detail: "Operating and free cash flow are positive." },
  { label: "Equity dilution", severity: "Medium", detected: false, detail: "No dilution event detected." },
  { label: "Pledged shares", severity: "High", detected: false, detail: "Promoter pledge is 0%." }
];
