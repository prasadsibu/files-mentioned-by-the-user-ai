export type Recommendation = "BUY" | "WATCH" | "IGNORE";

export type AnalyzeResponse = {
  recommendation: Recommendation;
  score: number;
};

export type ScoreItem = {
  label: string;
  score: number;
  weight: number;
  status: "positive" | "neutral" | "negative";
  reason: string;
};

export type Metric = {
  label: string;
  value: string;
  delta?: string;
  tone?: "positive" | "negative" | "neutral";
};

export type TrendPoint = {
  period: string;
  revenue: number;
  profit: number;
  eps: number;
  roe: number;
  roce: number;
  pe: number;
  price: number;
};

export type ShareholdingPoint = {
  quarter: string;
  promoter: number;
  fii: number;
  dii: number;
  retail: number;
};

export type NewsItem = {
  title: string;
  source: string;
  sentiment: "Positive" | "Neutral" | "Negative";
  score: number;
};

export type RiskItem = {
  label: string;
  severity: "Low" | "Medium" | "High";
  detected: boolean;
  detail: string;
};
