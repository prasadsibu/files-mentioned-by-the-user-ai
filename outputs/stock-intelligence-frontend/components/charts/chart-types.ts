export type FinancialTrendPoint = {
  period: string;
  revenue: number;
  profit: number;
  eps: number;
  roe: number;
  roce: number;
  pe: number;
  price: number;
};

export type ShareholdingTrendPoint = {
  quarter: string;
  promoter: number;
  fii: number;
  dii: number;
  retail: number;
  pledged_shares?: number;
};

export type ChartProps<T> = {
  data: T[];
  className?: string;
};
