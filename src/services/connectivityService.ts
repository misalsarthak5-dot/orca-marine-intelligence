export type ConnectivityStatus = 'ONLINE' | 'LIMITED' | 'OFFLINE';

export interface ConnectivityState {
  status: ConnectivityStatus;
  isOnline: boolean;
  isLimited: boolean;
  isOffline: boolean;
  lastSuccessfulSync: number | null;
  consecutiveFailures: number;
  failedServices: string[];
  activeReason: string;
}

const FAILURE_THRESHOLD = 2; // Needs at least 2 consecutive failures to enter LIMITED state

class ConnectivityService {
  private status: ConnectivityStatus = 'ONLINE';
  private lastSuccessfulSync: number | null = Date.now();
  private consecutiveFailures = 0;
  private failedServices = new Set<string>();
  private activeReason = 'All live telemetry services operational.';
  private listeners = new Set<(state: ConnectivityState) => void>();
  private recoveryListeners = new Set<() => Promise<void> | void>();

  constructor() {
    if (typeof window !== 'undefined') {
      this.status = navigator.onLine ? 'ONLINE' : 'OFFLINE';

      window.addEventListener('online', () => {
        this.handleNetworkOnline();
      });

      window.addEventListener('offline', () => {
        this.handleNetworkOffline();
      });
    }
  }

  private handleNetworkOnline() {
    if (this.status === 'OFFLINE') {
      this.consecutiveFailures = 0;
      this.failedServices.clear();
      this.status = 'ONLINE';
      this.activeReason = 'Network connection restored. Syncing live telemetry...';
      this.notifyListeners();
      this.triggerRecovery();
    }
  }

  private handleNetworkOffline() {
    this.status = 'OFFLINE';
    this.activeReason = 'No internet connection detected by device.';
    this.notifyListeners();
  }

  public getStatus(): ConnectivityStatus {
    return this.status;
  }

  public getState(): ConnectivityState {
    return {
      status: this.status,
      isOnline: this.status === 'ONLINE',
      isLimited: this.status === 'LIMITED',
      isOffline: this.status === 'OFFLINE',
      lastSuccessfulSync: this.lastSuccessfulSync,
      consecutiveFailures: this.consecutiveFailures,
      failedServices: Array.from(this.failedServices),
      activeReason: this.activeReason,
    };
  }

  /**
   * Record a successful live API request.
   * Clears consecutive failures and resets status to ONLINE if previously limited.
   */
  public recordSuccess(serviceName?: string) {
    this.lastSuccessfulSync = Date.now();
    this.consecutiveFailures = 0;
    if (serviceName) {
      this.failedServices.delete(serviceName);
    }

    if (typeof window !== 'undefined' && !navigator.onLine) {
      this.status = 'OFFLINE';
      this.activeReason = 'Device reports offline.';
    } else {
      this.status = 'ONLINE';
      this.activeReason = 'Live telemetry streaming normally.';
    }

    this.notifyListeners();
  }

  /**
   * Record a live API request failure or timeout.
   * Uses consecutiveFailures threshold to prevent transient glitches from triggering false LIMITED states.
   */
  public recordFailure(serviceName?: string, error?: any) {
    if (typeof window !== 'undefined' && !navigator.onLine) {
      this.status = 'OFFLINE';
      this.activeReason = 'Device is offline.';
      this.notifyListeners();
      return;
    }

    this.consecutiveFailures += 1;
    if (serviceName) {
      this.failedServices.add(serviceName);
    }

    if (this.consecutiveFailures >= FAILURE_THRESHOLD) {
      this.status = 'LIMITED';
      const svcList = Array.from(this.failedServices).join(', ');
      this.activeReason = svcList
        ? `Limited connectivity: live feed unavailable for ${svcList}. Showing verified cache.`
        : 'Limited connectivity: live API requests timing out. Showing verified cache.';
    }

    this.notifyListeners();
  }

  /**
   * Subscribe to connectivity state changes.
   */
  public subscribe(listener: (state: ConnectivityState) => void): () => void {
    this.listeners.add(listener);
    // Immediately invoke listener with current state
    listener(this.getState());
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Register a recovery callback triggered when connectivity returns.
   */
  public onRecovery(callback: () => Promise<void> | void): () => void {
    this.recoveryListeners.add(callback);
    return () => {
      this.recoveryListeners.delete(callback);
    };
  }

  /**
   * Trigger recovery callbacks to re-fetch live data.
   */
  public async triggerRecovery(): Promise<void> {
    const promises = Array.from(this.recoveryListeners).map((cb) => {
      try {
        return Promise.resolve(cb());
      } catch (e) {
        console.warn('[ConnectivityService] Recovery listener error:', e);
        return Promise.resolve();
      }
    });
    await Promise.allSettled(promises);
  }

  public getConsecutiveFailures(): number {
    return this.consecutiveFailures;
  }

  /**
   * Reset connectivity service state (useful for tests or re-initialization)
   */
  public reset() {
    this.status = typeof window !== 'undefined' && !navigator.onLine ? 'OFFLINE' : 'ONLINE';
    this.lastSuccessfulSync = Date.now();
    this.consecutiveFailures = 0;
    this.failedServices.clear();
    this.activeReason = 'All live telemetry services operational.';
    this.notifyListeners();
  }

  /**
   * Simulate offline/online state directly (useful for tests and offline preview toggles)
   */
  public setSimulatedOffline(offline: boolean) {
    if (offline) {
      this.status = 'OFFLINE';
      this.activeReason = 'Device is operating in offline simulation mode.';
    } else {
      this.status = 'ONLINE';
      this.consecutiveFailures = 0;
      this.failedServices.clear();
      this.activeReason = 'Live telemetry streaming normally.';
    }
    this.notifyListeners();
  }

  private notifyListeners() {
    const state = this.getState();
    this.listeners.forEach((listener) => {
      try {
        listener(state);
      } catch (e) {
        console.warn('[ConnectivityService] Listener notification error:', e);
      }
    });
  }
}

export const connectivityService = new ConnectivityService();

