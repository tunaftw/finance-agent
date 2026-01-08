// PodStock Dashboard Application

function dashboard() {
    return {
        // State
        loading: true,
        view: 'inbox',
        displayLimit: 50,
        inboxDisplayLimit: 50,

        // Data
        metadata: {},
        analyses: [],
        recommendations: [],
        sources: [],
        speakers: [],
        tickers: [],
        trackRecord: { by_source: [], by_speaker: [] },
        watchlist: [],

        // Filters
        filters: {
            search: '',
            action: '',
            tickerSearch: '',
        },

        // Inbox Filters
        inboxFilters: {
            dateRange: '',
            action: '',
            confidence: '',
            minTrust: '0',
            source: '',
            search: '',
        },

        // Computed
        get filteredRecommendations() {
            let results = this.recommendations;

            if (this.filters.search) {
                const search = this.filters.search.toLowerCase();
                results = results.filter(r =>
                    r.stock_name.toLowerCase().includes(search) ||
                    (r.ticker && r.ticker.toLowerCase().includes(search))
                );
            }

            if (this.filters.action) {
                results = results.filter(r => r.action === this.filters.action);
            }

            return results;
        },

        get filteredTickers() {
            if (!this.filters.tickerSearch) {
                return this.tickers;
            }

            const search = this.filters.tickerSearch.toLowerCase();
            return this.tickers.filter(t =>
                t.stock_name.toLowerCase().includes(search) ||
                (t.ticker && t.ticker.toLowerCase().includes(search))
            );
        },

        get filteredInbox() {
            let results = this.recommendations;

            // Date range filter
            if (this.inboxFilters.dateRange) {
                const now = new Date();
                let cutoff;
                switch (this.inboxFilters.dateRange) {
                    case '7d':
                        cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                        break;
                    case '30d':
                        cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                        break;
                    case '90d':
                        cutoff = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
                        break;
                    case '365d':
                        cutoff = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
                        break;
                }
                if (cutoff) {
                    results = results.filter(r => new Date(r.date) >= cutoff);
                }
            }

            // Action filter
            if (this.inboxFilters.action) {
                results = results.filter(r => r.action === this.inboxFilters.action);
            }

            // Confidence filter
            if (this.inboxFilters.confidence) {
                results = results.filter(r => r.confidence === this.inboxFilters.confidence);
            }

            // Trust filter
            const minTrust = parseInt(this.inboxFilters.minTrust) || 0;
            if (minTrust > 0) {
                results = results.filter(r => (r.trust_rating || r.source_trust || 0) >= minTrust);
            }

            // Source filter
            if (this.inboxFilters.source) {
                results = results.filter(r => r.source_id === this.inboxFilters.source);
            }

            // Search filter
            if (this.inboxFilters.search) {
                const search = this.inboxFilters.search.toLowerCase();
                results = results.filter(r =>
                    r.stock_name.toLowerCase().includes(search) ||
                    (r.ticker && r.ticker.toLowerCase().includes(search))
                );
            }

            // Sort by date descending (newest first)
            return results.sort((a, b) => new Date(b.date) - new Date(a.date));
        },

        // Initialization
        async init() {
            try {
                // Check for inline data first (embedded by generator to avoid CORS issues)
                if (window.DASHBOARD_DATA) {
                    const data = window.DASHBOARD_DATA;
                    this.metadata = data.metadata || {};
                    this.analyses = data.analyses || [];
                    this.recommendations = data.recommendations || [];
                    this.sources = data.sources || [];
                    this.speakers = data.speakers || [];
                    this.tickers = data.tickers || [];
                    this.trackRecord = data.trackRecord || { by_source: [], by_speaker: [] };
                    this.watchlist = data.watchlist || [];
                } else {
                    // Fallback to fetch (works when served via HTTP)
                    const [
                        metadata,
                        analyses,
                        recommendations,
                        sources,
                        speakers,
                        tickers,
                        trackRecord,
                        watchlist
                    ] = await Promise.all([
                        this.loadJson('data/metadata.json'),
                        this.loadJson('data/analyses.json'),
                        this.loadJson('data/recommendations.json'),
                        this.loadJson('data/sources.json'),
                        this.loadJson('data/speakers.json'),
                        this.loadJson('data/tickers.json'),
                        this.loadJson('data/track_record.json'),
                        this.loadJson('data/watchlist.json'),
                    ]);

                    this.metadata = metadata || {};
                    this.analyses = analyses || [];
                    this.recommendations = recommendations || [];
                    this.sources = sources || [];
                    this.speakers = speakers || [];
                    this.tickers = tickers || [];
                    this.trackRecord = trackRecord || { by_source: [], by_speaker: [] };
                    this.watchlist = watchlist || [];
                }

            } catch (error) {
                console.error('Error loading dashboard data:', error);
            } finally {
                this.loading = false;
            }
        },

        async loadJson(path) {
            try {
                const response = await fetch(path);
                if (!response.ok) {
                    console.warn(`Failed to load ${path}: ${response.status}`);
                    return null;
                }
                return await response.json();
            } catch (error) {
                console.warn(`Error loading ${path}:`, error);
                return null;
            }
        },

        // Helpers
        formatDate(dateStr) {
            if (!dateStr) return '-';
            return new Date(dateStr).toLocaleDateString('sv-SE');
        },

        formatReturn(value) {
            if (value === null || value === undefined) return '-';
            const prefix = value >= 0 ? '+' : '';
            return `${prefix}${value.toFixed(1)}%`;
        }
    };
}
