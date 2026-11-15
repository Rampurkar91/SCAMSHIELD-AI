export type RiskLevel = "low" | "moderate" | "high" | "critical";
export interface ScanRecord {
  id: number;
  kind: string;
  content: string;
  score: number;
  created_at: string;
  result: {
    score: number;
    level: RiskLevel;
    summary: string;
    indicators: Array<{ code: string; weight: number; reason: string }>;
    details: Record<string, unknown>;
    actions: string[];
    urls: string[];
    provider: { status: string; reason: string };
    limitations: string[];
  };
}
export interface IntegrationStatus {
  name: string;
  configured: boolean;
  availability: string;
  last_check: string | null;
  last_success: string | null;
  last_error: string | null;
}
export interface ThreatReport {
  id: number;
  category: string;
  description: string;
  status: string;
}
