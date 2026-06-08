export type Recommendation = "BUY" | "WATCH" | "IGNORE";

export type Fundamentals = {
  roe: number;
  roce: number;
  debt_equity: number;
  operating_cash_flow: number;
  free_cash_flow: number;
  eps: number;
};

export type Valuation = {
  pe: number;
  pb: number;
  peg: number;
  industry_pe: number;
  price: number;
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
  pledged_shares: number;
};

export type RiskItem = {
  label: string;
  severity: "Low" | "Medium" | "High" | string;
  detected: boolean;
  detail: string;
};

export type NewsItem = {
  title: string;
  source: string;
  published_at?: string | null;
  url: string;
  sentiment: "Positive" | "Neutral" | "Negative" | string;
  confidence: number;
  score: number;
};

export type NewsSentiment = {
  positive: number;
  neutral: number;
  negative: number;
  sentiment_score: number;
  article_count: number;
  articles: NewsItem[];
};

export type ConcallSignal = {
  label: string;
  detail: string;
  tone: "positive" | "neutral" | "negative" | string;
};

export type ConcallSummary = {
  final_view: string;
  confidence: number;
  reasoning: string;
  signals: ConcallSignal[];
};

export type ScoreItem = {
  label: string;
  score: number;
  weight: number;
  status: "positive" | "neutral" | "negative";
  reason: string;
};

export type ScoreBreakdownItem = {
  category: string;
  weight: number;
  score: number;
  weighted_score: number;
  reasoning: string;
};

export type AnalyzeResponse = {
  symbol: string;
  recommendation: Recommendation;
  score: number;
  fundamentals: Fundamentals;
  valuation: Valuation;
  trend_history: TrendPoint[];
  shareholding_history: ShareholdingPoint[];
  risk_flags: RiskItem[];
  news_sentiment: NewsSentiment;
  concall_summary: ConcallSummary;
  score_breakdown: ScoreBreakdownItem[];
};

export type Metric = {
  label: string;
  value: string;
  delta?: string;
  tone?: "positive" | "negative" | "neutral";
};
