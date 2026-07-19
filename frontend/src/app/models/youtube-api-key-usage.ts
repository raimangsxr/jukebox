export interface ApiKeyUsageItem {
  index: number;
  label: string;
  masked_suffix: string;
  used_count: number;
  remaining_count: number;
  daily_limit: number;
  exhausted: boolean;
}

export interface ApiKeyUsageListResponse {
  keys: ApiKeyUsageItem[];
  daily_limit: number;
  quota_day: string;
  next_reset_at: string;
}
