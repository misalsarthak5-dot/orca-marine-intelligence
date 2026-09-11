import { formatTimestampIST } from '../utils/freshness';

export interface CachedIntelligenceRecord<T = any> {
  key: string;
  entityType: string;
  locationKey: string;
  data: T;
  timestamp: number;
  formattedTime: string;
  source: string;
  metadata?: Record<string, any>;
}

const DB_NAME = 'orca_cache_db';
const DB_VERSION = 1;
const STORE_NAME = 'intelligence_cache';

// In-memory fallback map for SSR, tests, or environments without IndexedDB
const memoryStore = new Map<string, CachedIntelligenceRecord>();

/**
 * Format standard location cache key (e.g., "15.50_73.83" or location ID)
 */
export function getLocationKey(lat?: number, lon?: number, locationId?: string): string {
  if (lat !== undefined && lon !== undefined && !isNaN(lat) && !isNaN(lon)) {
    return `${lat.toFixed(2)}_${lon.toFixed(2)}`;
  }
  if (locationId) {
    return locationId.toLowerCase().trim();
  }
  return 'default_location';
}

/**
 * Open IndexedDB connection safely
 */
function openIndexedDB(): Promise<IDBDatabase | null> {
  if (typeof window === 'undefined' || !window.indexedDB) {
    return Promise.resolve(null);
  }

  return new Promise((resolve) => {
    try {
      const request = window.indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'key' });
          store.createIndex('entityType', 'entityType', { unique: false });
          store.createIndex('locationKey', 'locationKey', { unique: false });
          store.createIndex('timestamp', 'timestamp', { unique: false });
        }
      };

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => {
        console.warn('[CacheService] IndexedDB open error, using memory fallback:', request.error);
        resolve(null);
      };
    } catch (err) {
      console.warn('[CacheService] IndexedDB initialization failed, using memory fallback:', err);
      resolve(null);
    }
  });
}

export const cacheService = {
  /**
   * Retrieve a verified cached intelligence record.
   */
  async get<T = any>(entityType: string, locationKey: string): Promise<CachedIntelligenceRecord<T> | null> {
    const key = `${entityType}:${locationKey}`;

    // Try IndexedDB first
    const db = await openIndexedDB();
    if (db) {
      try {
        const record = await new Promise<CachedIntelligenceRecord<T> | null>((resolve) => {
          const tx = db.transaction(STORE_NAME, 'readonly');
          const store = tx.objectStore(STORE_NAME);
          const req = store.get(key);
          req.onsuccess = () => resolve(req.result || null);
          req.onerror = () => resolve(null);
        });

        if (record) {
          // Keep memoryStore in sync
          memoryStore.set(key, record);
          return record;
        }
      } catch (e) {
        console.warn('[CacheService] Error reading from IndexedDB:', e);
      }
    }

    // Fallback to in-memory store
    return (memoryStore.get(key) as CachedIntelligenceRecord<T>) || null;
  },

  /**
   * Save a verified intelligence record to cache.
   * NEVER caches failed responses or errors.
   */
  async set<T = any>(
    entityType: string,
    locationKey: string,
    data: T,
    source: string,
    metadata?: Record<string, any>
  ): Promise<void> {
    // ── DATA INTEGRITY VALIDATION ────────────────────────────────────
    // Reject failed responses, errors, or empty invalid data
    if (data === null || data === undefined) {
      return;
    }
    if (typeof data === 'object') {
      const anyData = data as any;
      if (anyData.status === 'error' || anyData.error || anyData.is_error) {
        return;
      }
    }

    const timestamp = Date.now();
    const formattedTime = formatTimestampIST(timestamp);
    const key = `${entityType}:${locationKey}`;

    const record: CachedIntelligenceRecord<T> = {
      key,
      entityType,
      locationKey,
      data,
      timestamp,
      formattedTime,
      source: typeof source === 'string' ? source : 'ORCA Cache',
      metadata,
    };

    // Always update in-memory store immediately
    memoryStore.set(key, record);

    // Persist to IndexedDB
    const db = await openIndexedDB();
    if (db) {
      try {
        await new Promise<void>((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, 'readwrite');
          const store = tx.objectStore(STORE_NAME);
          const req = store.put(record);
          req.onsuccess = () => resolve();
          req.onerror = () => reject(req.error);
        });
      } catch (e) {
        console.warn('[CacheService] Error writing to IndexedDB:', e);
      }
    }
  },

  /**
   * Save a verified intelligence record with an explicit timestamp (e.g. for historical or test fixtures).
   */
  async setWithTimestamp<T = any>(
    entityType: string,
    locationKey: string,
    data: T,
    timestamp: number,
    source?: string,
    metadata?: Record<string, any>
  ): Promise<void> {
    if (data === null || data === undefined) return;
    if (typeof data === 'object') {
      const anyData = data as any;
      if (anyData.status === 'error' || anyData.error || anyData.is_error) return;
    }

    const formattedTime = formatTimestampIST(timestamp);
    const key = `${entityType}:${locationKey}`;

    const record: CachedIntelligenceRecord<T> = {
      key,
      entityType,
      locationKey,
      data,
      timestamp,
      formattedTime,
      source: typeof source === 'string' ? source : 'ORCA Cache',
      metadata,
    };

    memoryStore.set(key, record);

    const db = await openIndexedDB();
    if (db) {
      try {
        await new Promise<void>((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, 'readwrite');
          const store = tx.objectStore(STORE_NAME);
          const req = store.put(record);
          req.onsuccess = () => resolve();
          req.onerror = () => reject(req.error);
        });
      } catch (e) {
        console.warn('[CacheService] Error writing to IndexedDB:', e);
      }
    }
  },

  /**
   * Delete a specific cached intelligence record
   */
  async delete(entityType: string, locationKey: string): Promise<void> {
    const key = `${entityType}:${locationKey}`;
    memoryStore.delete(key);

    const db = await openIndexedDB();
    if (db) {
      try {
        await new Promise<void>((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, 'readwrite');
          const store = tx.objectStore(STORE_NAME);
          const req = store.delete(key);
          req.onsuccess = () => resolve();
          req.onerror = () => reject(req.error);
        });
      } catch (e) {
        console.warn('[CacheService] Error deleting from IndexedDB:', e);
      }
    }
  },

  /**
   * Check if a cached record exists
   */
  async has(entityType: string, locationKey: string): Promise<boolean> {
    const record = await this.get(entityType, locationKey);
    return record !== null;
  },

  /**
   * Get all cached records for a specific coastal location
   */
  async getAllForLocation(locationKey: string): Promise<Record<string, CachedIntelligenceRecord>> {
    const results: Record<string, CachedIntelligenceRecord> = {};
    const entities = ['marine', 'weather', 'safety', 'hazards', 'pfz', 'route', 'location', 'ocean_data', 'safety_assessment', 'incois_pfz', 'route_intelligence'];

    for (const entity of entities) {
      const rec = await this.get(entity, locationKey);
      if (rec) {
        results[entity] = rec;
      }
    }

    return results;
  },

  /**
   * Clear all or namespace-specific cached intelligence
   */
  async clear(entityType?: string): Promise<void> {
    if (entityType) {
      for (const key of Array.from(memoryStore.keys())) {
        if (key.startsWith(`${entityType}:`)) {
          memoryStore.delete(key);
        }
      }
      return;
    }

    memoryStore.clear();

    const db = await openIndexedDB();
    if (db) {
      try {
        await new Promise<void>((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, 'readwrite');
          const store = tx.objectStore(STORE_NAME);
          const req = store.clear();
          req.onsuccess = () => resolve();
          req.onerror = () => reject(req.error);
        });
      } catch (e) {
        console.warn('[CacheService] Error clearing IndexedDB:', e);
      }
    }
  },
};
