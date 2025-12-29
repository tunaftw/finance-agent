// PodStock Dashboard Application

function dashboard() {
    return {
        // State
        loading: true,
        view: 'inbox',
        displayLimit: 50,
        inboxDisplayLimit: 50,
        podcastDisplayLimit: 50,
        twitterDisplayLimit: 100,
        youtubeDisplayLimit: 50,

        // Data
        metadata: {},
        analyses: [],
        recommendations: [],
        sources: [],

        // Source-specific data
        podcasts: {
            episodes: [],
            sources: [],
            stock_mentions: []
        },
        twitter: {
            tweets: [],
            users: [],
            stock_mentions: []
        },
        youtube: {
            videos: [],
            channels: [],
            stock_mentions: []
        },

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

        // Podcast Filters
        podcastFilters: {
            source: '',
            dateFrom: '',
            dateTo: '',
            companySearch: '',
        },

        // Twitter Filters
        twitterFilters: {
            user: '',
            dateFrom: '',
            dateTo: '',
            companySearch: '',
            onlyActionable: false,
        },

        // YouTube Filters
        youtubeFilters: {
            channel: '',
            dateFrom: '',
            dateTo: '',
            companySearch: '',
        },

        // === INBOX COMPUTED ===

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

        // === PODCAST COMPUTED ===

        get podcastSources() {
            return this.podcasts.sources || [];
        },

        get filteredPodcastEpisodes() {
            let results = this.podcasts.episodes || [];

            // Source filter
            if (this.podcastFilters.source) {
                results = results.filter(e => e.podcast_id === this.podcastFilters.source);
            }

            // Date from filter
            if (this.podcastFilters.dateFrom) {
                results = results.filter(e => e.date >= this.podcastFilters.dateFrom);
            }

            // Date to filter
            if (this.podcastFilters.dateTo) {
                results = results.filter(e => e.date <= this.podcastFilters.dateTo);
            }

            // Company search
            if (this.podcastFilters.companySearch) {
                const search = this.podcastFilters.companySearch.toLowerCase();
                results = results.filter(e =>
                    (e.stocks_discussed || []).some(s => s.toLowerCase().includes(search)) ||
                    (e.recommendations || []).some(r =>
                        r.stock_name.toLowerCase().includes(search) ||
                        (r.ticker && r.ticker.toLowerCase().includes(search))
                    )
                );
            }

            // Sort by date descending
            return results.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
        },

        // === TWITTER COMPUTED ===

        get twitterUsers() {
            return this.twitter.users || [];
        },

        get filteredTweets() {
            let results = this.twitter.tweets || [];

            // User filter
            if (this.twitterFilters.user) {
                results = results.filter(t => t.user_id === this.twitterFilters.user);
            }

            // Date from filter
            if (this.twitterFilters.dateFrom) {
                results = results.filter(t => t.date >= this.twitterFilters.dateFrom);
            }

            // Date to filter
            if (this.twitterFilters.dateTo) {
                results = results.filter(t => t.date <= this.twitterFilters.dateTo);
            }

            // Company search
            if (this.twitterFilters.companySearch) {
                const search = this.twitterFilters.companySearch.toLowerCase();
                results = results.filter(t =>
                    (t.stock_mentions || []).some(m =>
                        m.stock_name.toLowerCase().includes(search) ||
                        (m.ticker && m.ticker.toLowerCase().includes(search))
                    )
                );
            }

            // Only actionable filter
            if (this.twitterFilters.onlyActionable) {
                results = results.filter(t => t.is_actionable);
            }

            // Sort by date descending
            return results.sort((a, b) => (b.posted_at || '').localeCompare(a.posted_at || ''));
        },

        get crossReferencedStocks() {
            let stocks = this.twitter.stock_mentions || [];

            // If searching, filter to matching stocks
            if (this.twitterFilters.companySearch) {
                const search = this.twitterFilters.companySearch.toLowerCase();
                stocks = stocks.filter(s =>
                    s.stock_name.toLowerCase().includes(search) ||
                    (s.ticker && s.ticker.toLowerCase().includes(search))
                );
            } else {
                // Show stocks mentioned by 2+ users
                stocks = stocks.filter(s => s.unique_users >= 2);
            }

            return stocks.sort((a, b) => b.total_mentions - a.total_mentions);
        },

        // === YOUTUBE COMPUTED ===

        get youtubeChannels() {
            return this.youtube.channels || [];
        },

        get filteredYoutubeVideos() {
            let results = this.youtube.videos || [];

            // Channel filter
            if (this.youtubeFilters.channel) {
                results = results.filter(v => v.channel_id === this.youtubeFilters.channel);
            }

            // Date from filter
            if (this.youtubeFilters.dateFrom) {
                results = results.filter(v => v.date >= this.youtubeFilters.dateFrom);
            }

            // Date to filter
            if (this.youtubeFilters.dateTo) {
                results = results.filter(v => v.date <= this.youtubeFilters.dateTo);
            }

            // Company search
            if (this.youtubeFilters.companySearch) {
                const search = this.youtubeFilters.companySearch.toLowerCase();
                results = results.filter(v =>
                    (v.stocks_discussed || []).some(s =>
                        (typeof s === 'string' ? s : String(s)).toLowerCase().includes(search)
                    ) ||
                    (v.recommendations || []).some(r =>
                        r.stock_name.toLowerCase().includes(search) ||
                        (r.ticker && r.ticker.toLowerCase().includes(search))
                    )
                );
            }

            // Sort by date descending
            return results.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
        },

        // === INITIALIZATION ===

        async init() {
            try {
                // Check for inline data first (embedded by generator to avoid CORS issues)
                if (window.DASHBOARD_DATA) {
                    const data = window.DASHBOARD_DATA;
                    this.metadata = data.metadata || {};
                    this.analyses = data.analyses || [];
                    this.recommendations = data.recommendations || [];
                    this.sources = data.sources || [];

                    // Load source-specific data
                    this.podcasts = data.podcasts || { episodes: [], sources: [], stock_mentions: [] };
                    this.twitter = data.twitter || { tweets: [], users: [], stock_mentions: [] };
                    this.youtube = data.youtube || { videos: [], channels: [], stock_mentions: [] };
                } else {
                    // Fallback to fetch (works when served via HTTP)
                    const [
                        metadata,
                        analyses,
                        recommendations,
                        sources,
                        podcasts,
                        twitter,
                        youtube
                    ] = await Promise.all([
                        this.loadJson('data/metadata.json'),
                        this.loadJson('data/analyses.json'),
                        this.loadJson('data/recommendations.json'),
                        this.loadJson('data/sources.json'),
                        this.loadJson('data/podcasts.json'),
                        this.loadJson('data/twitter.json'),
                        this.loadJson('data/youtube.json'),
                    ]);

                    this.metadata = metadata || {};
                    this.analyses = analyses || [];
                    this.recommendations = recommendations || [];
                    this.sources = sources || [];
                    this.podcasts = podcasts || { episodes: [], sources: [], stock_mentions: [] };
                    this.twitter = twitter || { tweets: [], users: [], stock_mentions: [] };
                    this.youtube = youtube || { videos: [], channels: [], stock_mentions: [] };
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

        // === HELPERS ===

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
