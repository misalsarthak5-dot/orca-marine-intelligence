import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

import { cacheService, getLocationKey } from '../services/cacheService';
import { connectivityService } from '../services/connectivityService';
import { evaluateFreshness, formatFreshnessAge, isDataStale } from '../utils/freshness';
import { getVerifiedOceanData } from '../services/orcaDataService';
import { getVerifiedSafetyAssessment } from '../services/safetyService';
import { getVerifiedPFZData } from '../services/pfzService';
import { getVerifiedRouteAnalysis, getRouteCacheKey } from '../services/routeService';

describe('1. Freshness & Live Labeling Evaluation', () => {
  const NOW = Date.now();
  const ONE_MIN_AGO = NOW - 60 * 1000;
  const TWO_HOURS_AGO = NOW - 2 * 60 * 60 * 1000;

  it('evaluates LIVE when current API request succeeded', () => {
    const result = evaluateFreshness({
      isLive: true,
      dataTimestamp: NOW,
      thresholdMinutes: 60,
    });
    assert.strictEqual(result.status, 'LIVE');
    assert.strictEqual(result.isLive, true);
    assert.strictEqual(result.isStale, false);
    assert.strictEqual(result.label, 'Live');
  });

  it('evaluates CACHED when live request failed and valid cached data exists (within threshold)', () => {
    const result = evaluateFreshness({
      isLive: false,
      dataTimestamp: ONE_MIN_AGO,
      thresholdMinutes: 60,
    });
    assert.strictEqual(result.status, 'CACHED');
    assert.strictEqual(result.isLive, false);
    assert.strictEqual(result.isStale, false);
    assert.strictEqual(result.label, 'Cached');
  });

  it('evaluates STALE when cached data exists but exceeds the configured freshness threshold', () => {
    const result = evaluateFreshness({
      isLive: false,
      dataTimestamp: TWO_HOURS_AGO,
      thresholdMinutes: 60,
    });
    assert.strictEqual(result.status, 'STALE');
    assert.strictEqual(result.isLive, false);
    assert.strictEqual(result.isStale, true);
    assert.strictEqual(result.label, 'Stale');
    assert.strictEqual(isDataStale(TWO_HOURS_AGO, 60), true);
  });

  it('evaluates UNAVAILABLE when neither live data nor cached data exists', () => {
    const result = evaluateFreshness({
      isLive: false,
      dataTimestamp: null,
      thresholdMinutes: 60,
    });
    assert.strictEqual(result.status, 'UNAVAILABLE');
    assert.strictEqual(result.isLive, false);
    assert.strictEqual(result.isStale, true);
    assert.strictEqual(result.label, 'Unavailable');
  });

  it('STRICT: NEVER labels cached data as "Live", regardless of age', () => {
    // Even if cached 1 millisecond ago, if isLive is false, it MUST be CACHED, not LIVE
    const justNowCached = evaluateFreshness({
      isLive: false,
      dataTimestamp: NOW - 5,
      thresholdMinutes: 60,
    });
    assert.notStrictEqual(justNowCached.status, 'LIVE');
    assert.strictEqual(justNowCached.status, 'CACHED');
    assert.strictEqual(justNowCached.isLive, false);
  });

  it('formats freshness age correctly', () => {
    assert.strictEqual(formatFreshnessAge(NOW, 'en'), 'Just now');
    assert.strictEqual(formatFreshnessAge(NOW - 5 * 60 * 1000, 'en'), '5 min ago');
    assert.strictEqual(formatFreshnessAge(NOW - 2 * 60 * 60 * 1000, 'en'), '2h ago');
    assert.strictEqual(formatFreshnessAge(null, 'en'), 'No data');
  });
});

describe('2. Connectivity State & Consecutive Failure Handling', () => {
  beforeEach(() => {
    connectivityService.reset();
  });

  it('starts in ONLINE state when live requests are succeeding', () => {
    connectivityService.recordSuccess('weather');
    assert.strictEqual(connectivityService.getStatus(), 'ONLINE');
    assert.strictEqual(connectivityService.getConsecutiveFailures(), 0);
  });

  it('does NOT switch to LIMITED after a single transient API failure', () => {
    connectivityService.recordSuccess('weather');
    connectivityService.recordFailure('weather', 'Temporary timeout');
    
    // With 1 failure, it should remain ONLINE to avoid false alarms
    assert.strictEqual(connectivityService.getConsecutiveFailures(), 1);
    assert.strictEqual(connectivityService.getStatus(), 'ONLINE');
  });

  it('switches to LIMITED when consecutive API failures reach threshold (>= 2)', () => {
    connectivityService.recordFailure('weather', 'Timeout 1');
    connectivityService.recordFailure('weather', 'Timeout 2');
    
    assert.strictEqual(connectivityService.getConsecutiveFailures(), 2);
    assert.strictEqual(connectivityService.getStatus(), 'LIMITED');
  });

  it('recovers from LIMITED back to ONLINE immediately upon a successful request', () => {
    connectivityService.recordFailure('weather', 'Timeout 1');
    connectivityService.recordFailure('weather', 'Timeout 2');
    assert.strictEqual(connectivityService.getStatus(), 'LIMITED');

    connectivityService.recordSuccess('weather');
    assert.strictEqual(connectivityService.getConsecutiveFailures(), 0);
    assert.strictEqual(connectivityService.getStatus(), 'ONLINE');
  });

  it('handles offline simulation and status listener notifications', () => {
    const states: string[] = [];
    const unsubscribe = connectivityService.subscribe((state) => {
      states.push(state.status);
    });

    connectivityService.setSimulatedOffline(true);
    assert.strictEqual(connectivityService.getStatus(), 'OFFLINE');

    connectivityService.setSimulatedOffline(false);
    assert.strictEqual(connectivityService.getStatus(), 'ONLINE');

    unsubscribe();
    assert.ok(states.includes('OFFLINE'));
  });
});

describe('3. Cache Service Integrity & Operations', () => {
  beforeEach(async () => {
    await cacheService.clear();
  });

  it('stores and retrieves verified cache entries with timestamp metadata', async () => {
    const payload = { wave_height: 1.2, wind_speed: 14.5 };
    await cacheService.set('marine_data', 'test_loc_1', payload, 'Open-Meteo');

    const cached = await cacheService.get('marine_data', 'test_loc_1');
    assert.ok(cached);
    assert.deepStrictEqual(cached.data, payload);
    assert.strictEqual(isDataStale(cached.timestamp, 60), false);
    assert.ok(typeof cached.timestamp === 'number');
  });

  it('rejects storing invalid/error responses into verified cache', async () => {
    const errorPayload = { status: 'error', detail: 'Internal API Server Error' };
    await cacheService.set('marine_data', 'bad_loc', errorPayload, 'Error Source');

    const cached = await cacheService.get('marine_data', 'bad_loc');
    assert.strictEqual(cached, null, 'Error responses must never be stored in verified cache');
  });

  it('deletes specific entries and clears whole namespace', async () => {
    await cacheService.set('marine_data', 'loc_a', { a: 1 }, 'test_source');
    await cacheService.set('marine_data', 'loc_b', { b: 2 }, 'test_source');

    await cacheService.delete('marine_data', 'loc_a');
    assert.strictEqual(await cacheService.get('marine_data', 'loc_a'), null);
    assert.ok(await cacheService.get('marine_data', 'loc_b'));

    await cacheService.clear('marine_data');
    assert.strictEqual(await cacheService.get('marine_data', 'loc_b'), null);
  });
});

describe('4. Data Service Fallback & Cache Flow Integration', () => {
  beforeEach(async () => {
    await cacheService.clear();
    connectivityService.reset();
  });

  it('returns UNAVAILABLE when API fails and no cache exists', async () => {
    // Calling for coordinates that will fail when backend is unreachable in isolated test
    // with forced empty cache
    const result = await getVerifiedOceanData(99.99, 99.99, {
      skipLive: true, // Simulates offline / network unreachable
    });

    assert.strictEqual(result.data, null);
    assert.strictEqual(result.freshness.status, 'UNAVAILABLE');
    assert.strictEqual(result.freshness.isLive, false);
  });

  it('returns CACHED with proper timestamp when API fails but verified cache exists', async () => {
    // Seed verified cache first
    const dummyTelemetry = {
      latitude: 15.5,
      longitude: 73.83,
      current: {
        wave_height: 1.1,
        wind_speed_10m: 12.0,
        wind_direction_10m: 240,
        sea_surface_temperature: 28.5,
      },
    };
    const key = getLocationKey(15.5, 73.83);
    await cacheService.set('marine_data', key, dummyTelemetry, 'Open-Meteo');

    // Now request with skipLive=true (simulating live network failure)
    const result = await getVerifiedOceanData(15.5, 73.83, { skipLive: true });

    assert.ok(result.data);
    assert.strictEqual(result.freshness.status, 'CACHED');
    assert.strictEqual(result.freshness.isLive, false);
    assert.strictEqual(result.freshness.isStale, false);
    assert.strictEqual(result.data.current.wave_height, 1.1);
  });

  it('returns STALE when verified cached data is older than threshold', async () => {
    const oldTimestamp = Date.now() - 3 * 60 * 60 * 1000; // 3 hours ago
    const dummyTelemetry = {
      latitude: 15.5,
      longitude: 73.83,
      current: { wave_height: 1.8 },
    };
    const key = getLocationKey(15.5, 73.83);
    await cacheService.setWithTimestamp('marine_data', key, dummyTelemetry, oldTimestamp, 'Open-Meteo');

    const result = await getVerifiedOceanData(15.5, 73.83, { skipLive: true, thresholdMinutes: 60 });

    assert.ok(result.data);
    assert.strictEqual(result.freshness.status, 'STALE');
    assert.strictEqual(result.freshness.isStale, true);
    assert.strictEqual(result.freshness.isLive, false);
  });

  it('PFZ Service: returns CACHED INCOIS PFZ when offline with valid cache', async () => {
    const dummyPFZ = {
      status: 'success',
      latitude: 15.5,
      longitude: 73.83,
      advisories_count: 2,
      advisories: [
        { landing_center: 'Malpe', distance_from_query_km: 15.2, bearing_deg: 240, advisory_text: 'PFZ Active' }
      ],
      regional_features_count: 5,
      regional_features: [],
    };
    const key = getLocationKey(15.5, 73.83);
    await cacheService.set('pfz', key, dummyPFZ, 'INCOIS GeoServer WFS');

    const result = await getVerifiedPFZData(15.5, 73.83, { skipLive: true });
    assert.ok(result.data);
    assert.strictEqual(result.freshness.status, 'CACHED');
    assert.strictEqual(result.data.advisories_count, 2);
  });

  it('Route Service: returns CACHED Route Analysis when offline with valid cache', async () => {
    const dummyRoute = {
      origin: { name: 'Goa Coast', latitude: 15.5, longitude: 73.83 },
      destination: { name: 'Target Alpha', latitude: 15.4, longitude: 73.6 },
      recommended_route_id: 'route_1',
      routes: [
        {
          id: 'route_1',
          name: 'Direct Marine Corridor',
          risk_level: 'LOW',
          coordinates: [[15.5, 73.83], [15.4, 73.6]],
          estimated_time_hours: 1.2,
          conditions: { peak_wave_m: 1.0, peak_wind_kt: 10 },
          description: 'Clear corridor',
        }
      ],
    };
    const routeKey = getRouteCacheKey(15.5, 73.83, 15.4, 73.6);
    await cacheService.set('route', routeKey, dummyRoute, 'ORCA Route Intelligence');

    const result = await getVerifiedRouteAnalysis(
      { name: 'Goa Coast', latitude: 15.5, longitude: 73.83 },
      { name: 'Target Alpha', latitude: 15.4, longitude: 73.6 },
      { skipLive: true }
    );

    assert.ok(result.data);
    assert.strictEqual(result.freshness.status, 'CACHED');
    assert.strictEqual(result.data.recommended_route_id, 'route_1');
  });

  it('Safety Service: returns Previous Verified Assessment when offline with cache', async () => {
    const dummyAssessment = {
      status: 'success',
      score: 88,
      risk_level: 'LOW',
      safety_category: 'SAFE',
      summary: 'Safe conditions observed',
    };
    const key = getLocationKey(15.5, 73.83);
    await cacheService.set('safety', key, dummyAssessment, 'ORCA Safety Engine');

    const result = await getVerifiedSafetyAssessment(15.5, 73.83, { skipLive: true });
    assert.ok(result.data);
    assert.strictEqual(result.freshness?.status, 'CACHED');
    assert.strictEqual(result.data.score, 88);
  });
});
