import type { Language } from '../types/index.ts';

export type DataFreshnessStatus = 'LIVE' | 'CACHED' | 'STALE' | 'UNAVAILABLE';

export interface FreshnessEvaluation {
  status: DataFreshnessStatus;
  timestamp: number | null;
  formattedTime: string;
  ageText: string;
  isStale: boolean;
  isCached: boolean;
  isLive: boolean;
  isUnavailable: boolean;
  label: string;
  warningNotice?: string;
}

/** Default freshness threshold: 60 minutes */
export const DEFAULT_STALE_THRESHOLD_MINUTES = 60;

/**
 * Format a relative age string (e.g. "2 min ago", "24 min ago", "3h 12m ago").
 */
export function formatAge(timestampMs: number | null | undefined, lang: Language = 'en'): string {
  if (timestampMs === null || timestampMs === undefined || isNaN(timestampMs) || timestampMs <= 0) {
    return lang === 'hi' ? 'कोई डेटा नहीं' : lang === 'mr' ? 'माहिती नाही' : 'No data';
  }
  const diffMs = Math.max(0, Date.now() - timestampMs);
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHours = Math.floor(diffMin / 60);
  const remMin = diffMin % 60;

  if (lang === 'hi') {
    if (diffMin < 1) return 'अभी-अभी';
    if (diffMin < 60) return `${diffMin} मिनट पहले`;
    if (remMin === 0) return `${diffHours} घंटे पहले`;
    return `${diffHours} घंटे ${remMin} मिनट पहले`;
  }

  if (lang === 'mr') {
    if (diffMin < 1) return 'आत्ताच';
    if (diffMin < 60) return `${diffMin} मिनिटांपूर्वी`;
    if (remMin === 0) return `${diffHours} तासांपूर्वी`;
    return `${diffHours} तास ${remMin} मिनिटांपूर्वी`;
  }

  // English default
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin} min ago`;
  if (diffHours < 24) {
    if (remMin === 0) return `${diffHours}h ago`;
    return `${diffHours}h ${remMin}m ago`;
  }
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

/**
 * Format timestamp into standard IST string (e.g. "18:42 IST").
 */
export function formatTimestampIST(timestampMs: number): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Kolkata',
      hour12: false,
    }).format(new Date(timestampMs)) + ' IST';
  } catch {
    const d = new Date(timestampMs);
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')} IST`;
  }
}

/**
 * Check if a timestamp is stale beyond threshold
 */
export function isDataStale(
  timestampMs: number | null | undefined,
  thresholdMinutes: number = DEFAULT_STALE_THRESHOLD_MINUTES
): boolean {
  if (!timestampMs || isNaN(timestampMs)) return true;
  const ageMs = Math.max(0, Date.now() - timestampMs);
  return Math.floor(ageMs / (1000 * 60)) >= thresholdMinutes;
}

export const formatFreshnessAge = formatAge;

export interface EvaluateFreshnessOptions {
  isLive: boolean;
  dataTimestamp?: number | null;
  thresholdMinutes?: number;
  lang?: Language;
}

/**
 * Rigorously evaluate the freshness status of a piece of intelligence.
 * 
 * Supports both object parameter ({ isLive, dataTimestamp, thresholdMinutes, lang })
 * and positional parameters (isLiveResponse, timestampMs, staleThresholdMinutes, lang).
 * 
 * Rules:
 * 1. LIVE: Current API request succeeded in this session.
 * 2. CACHED: Live request failed, and verified cached data is being displayed.
 * 3. STALE: Cached data exists but age exceeds the stale threshold.
 * 4. UNAVAILABLE: Neither live nor cached data is available.
 * 
 * Note: Cached data is NEVER labelled as LIVE.
 */
export function evaluateFreshness(
  arg1: boolean | EvaluateFreshnessOptions,
  timestampMs?: number | null,
  staleThresholdMinutes: number = DEFAULT_STALE_THRESHOLD_MINUTES,
  lang: Language = 'en'
): FreshnessEvaluation {
  let isLiveResponse = false;
  let targetTimestamp: number | null = null;
  let threshold = staleThresholdMinutes;
  let language = lang;

  if (typeof arg1 === 'object' && arg1 !== null) {
    isLiveResponse = Boolean(arg1.isLive);
    targetTimestamp = arg1.dataTimestamp !== undefined ? arg1.dataTimestamp : null;
    threshold = arg1.thresholdMinutes !== undefined ? arg1.thresholdMinutes : DEFAULT_STALE_THRESHOLD_MINUTES;
    language = arg1.lang || 'en';
  } else {
    isLiveResponse = Boolean(arg1);
    targetTimestamp = timestampMs !== undefined ? timestampMs : null;
    threshold = staleThresholdMinutes;
    language = lang;
  }

  if (targetTimestamp === null || targetTimestamp === undefined || isNaN(targetTimestamp)) {
    return {
      status: 'UNAVAILABLE',
      timestamp: null,
      formattedTime: 'N/A',
      ageText: 'No data',
      isStale: true,
      isCached: false,
      isLive: false,
      isUnavailable: true,
      label: 'Unavailable',
      warningNotice: language === 'hi'
        ? 'कोई लाइव या कैश्ड डेटा उपलब्ध नहीं है।'
        : language === 'mr'
        ? 'कोणताही थेट किंवा कॅश डेटा उपलब्ध नाही.'
        : 'Neither live telemetry nor verified cached data is available.',
    };
  }

  const ageMs = Math.max(0, Date.now() - targetTimestamp);
  const ageMinutes = Math.floor(ageMs / (1000 * 60));
  const ageText = formatAge(targetTimestamp, language);
  const formattedTime = formatTimestampIST(targetTimestamp);

  if (isLiveResponse) {
    return {
      status: 'LIVE',
      timestamp: targetTimestamp,
      formattedTime,
      ageText,
      isStale: false,
      isCached: false,
      isLive: true,
      isUnavailable: false,
      label: 'Live',
    };
  }

  const isStale = ageMinutes >= threshold;
  const status: DataFreshnessStatus = isStale ? 'STALE' : 'CACHED';

  let label = isStale ? 'Stale' : 'Cached';
  let warningNotice = '';

  if (isStale) {
    warningNotice = language === 'hi'
      ? `कैश्ड डेटा (${formattedTime}) पुराना है। वर्तमान समुद्री स्थितियां भिन्न हो सकती हैं।`
      : language === 'mr'
      ? `कॅश डेटा (${formattedTime}) जुना झाला आहे. सद्य सागरी परिस्थिती बदललेली असू शकते.`
      : `Cached data from ${formattedTime} is stale. Live conditions may have changed significantly. Reconnect before relying on this assessment.`;
  } else {
    warningNotice = language === 'hi'
      ? `अंतिम सत्यापित कैश्ड डेटा (${formattedTime}) प्रदर्शित किया जा रहा है।`
      : language === 'mr'
      ? `शेवटचा सत्यापित कॅश डेटा (${formattedTime}) दर्शवत आहे.`
      : `Showing last verified data from ${formattedTime}. Reconnect to refresh live telemetry.`;
  }

  return {
    status,
    timestamp: targetTimestamp,
    formattedTime,
    ageText,
    isStale,
    isCached: true,
    isLive: false,
    isUnavailable: false,
    label,
    warningNotice,
  };
}
