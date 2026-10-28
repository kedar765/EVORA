"use client";

import React from "react";
import AIInsights from "./AIInsights";
import { UploadResult, FullDatasetData } from "./types";

interface AnalyticsAgentProps {
  uploadResult?: UploadResult | null;
  fullDataset?: FullDatasetData | null;
  isLoading?: boolean;
  analyticsData?: unknown;
  error?: string;
}

export default function AnalyticsAgent({
  uploadResult = null,
  fullDataset = null,
  isLoading = false,
}: AnalyticsAgentProps) {
  return (
    <AIInsights
      uploadResult={uploadResult}
      fullDataset={fullDataset}
      isLoading={isLoading}
    />
  );
}
