// PodStock Dashboard Application

function dashboard() {
    return {
        // State
        loading: true,
        loadSource: 'none',  // 'inline' | 'fetch'
        loadErrors: [],      // Track failed data loads
        view: 'podcast',
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
            sources: [],           // Multi-select array
            datePreset: '',        // '7d', '30d', '90d', 'ytd', ''
            dateFrom: '',          // Custom date (used if datePreset is empty)
            dateTo: '',            // Custom date
            companySearch: '',
            positionDisclosure: '',
            action: '',            // 'buy', 'sell', 'hold', 'watch', 'avoid'
            confidence: '',        // 'high', 'medium', 'low'
            hasPriceTarget: false, // Filter for recs with price targets
        },

        // Podcast UI state
        podcastDropdownOpen: false,
        podcastSourceSearch: '',

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
            recommendationType: '',
        },

        // Filings data and state
        filings: {
            companies: [],
            evolutions: {},
            theses: {}
        },
        selectedFilingCompany: '',
        filingsSubView: 'promises',
        expandedTonePeriod: null,  // For click-to-expand tone details

        // Alpha data and state
        alpha: {
            companies: [],
            analyses: {},
            history: {}
        },
        selectedAlphaCompany: '',
        alphaSubView: 'overview',  // overview, fundamentals, sentiment, risks, position

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

            // Multi-select source filter
            if (this.podcastFilters.sources.length > 0) {
                results = results.filter(e => this.podcastFilters.sources.includes(e.podcast_id));
            }

            // Date filter (preset or custom)
            const dateRange = this.getPodcastDateRange();
            if (dateRange.from) {
                results = results.filter(e => e.date >= dateRange.from);
            }
            if (dateRange.to) {
                results = results.filter(e => e.date <= dateRange.to);
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

            // Position disclosure filter
            if (this.podcastFilters.positionDisclosure) {
                const disclosure = this.podcastFilters.positionDisclosure;
                results = results.filter(e =>
                    (e.stock_segments || []).some(seg => seg.position_disclosure === disclosure)
                );
            }

            // Action filter (filter episodes that have at least one rec with this action)
            if (this.podcastFilters.action) {
                const action = this.podcastFilters.action;
                results = results.filter(e =>
                    (e.recommendations || []).some(r => r.action === action)
                );
            }

            // Confidence filter
            if (this.podcastFilters.confidence) {
                const confidence = this.podcastFilters.confidence;
                results = results.filter(e =>
                    (e.recommendations || []).some(r => r.confidence === confidence)
                );
            }

            // Price target filter
            if (this.podcastFilters.hasPriceTarget) {
                results = results.filter(e =>
                    (e.recommendations || []).some(r => r.price_target)
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

            // Recommendation type filter
            if (this.youtubeFilters.recommendationType) {
                const recType = this.youtubeFilters.recommendationType;
                results = results.filter(v =>
                    (v.recommendations || []).some(r => r.recommendation_type === recType)
                );
            }

            // Sort by date descending
            return results.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
        },

        // === FILINGS COMPUTED ===

        get filingCompanies() {
            return this.filings.companies || [];
        },

        get currentThesis() {
            if (!this.selectedFilingCompany) return null;
            return this.filings.theses[this.selectedFilingCompany] || null;
        },

        get currentEvolution() {
            if (!this.selectedFilingCompany) return null;
            return this.filings.evolutions[this.selectedFilingCompany] || null;
        },

        get sortedPromises() {
            if (!this.currentEvolution) return [];
            const promises = this.currentEvolution.promises || [];
            // Sort by most recent quarter first
            return [...promises].sort((a, b) => {
                const quarterOrder = (q) => {
                    if (!q) return 0;
                    const match = q.match(/Q(\d)\s*(\d{4})/);
                    if (match) return parseInt(match[2]) * 10 + parseInt(match[1]);
                    return 0;
                };
                return quarterOrder(b.quarter_made) - quarterOrder(a.quarter_made);
            });
        },

        get toneDataPoints() {
            if (!this.currentEvolution) return [];
            return this.currentEvolution.tone_trajectory || [];
        },

        get financialTrends() {
            if (!this.currentEvolution) return null;
            return this.currentEvolution.financial_trends || null;
        },

        get philosophyAlignment() {
            if (!this.currentThesis) return null;
            return this.currentThesis.philosophy_alignment || null;
        },

        // Helper to get status color class
        getPromiseStatusClass(status) {
            switch (status) {
                case 'met': return 'bg-green-100 text-green-800';
                case 'on_track': return 'bg-blue-100 text-blue-800';
                case 'missed': return 'bg-red-100 text-red-800';
                default: return 'bg-gray-100 text-gray-800';
            }
        },

        // Helper to get tone color class
        getToneClass(tone) {
            switch (tone) {
                case 'optimistic': return 'bg-green-500';
                case 'cautiously_optimistic': return 'bg-green-300';
                case 'neutral': return 'bg-gray-400';
                case 'cautious': return 'bg-yellow-500';
                case 'defensive': return 'bg-red-500';
                default: return 'bg-gray-300';
            }
        },

        // Helper to get philosophy alignment class
        getPhilosophyClass(value) {
            if (!value) return 'border-gray-200 bg-gray-50';
            if (value.startsWith('POSITIVE')) return 'border-green-300 bg-green-50';
            if (value.startsWith('NEGATIVE')) return 'border-red-300 bg-red-50';
            return 'border-yellow-300 bg-yellow-50';
        },

        // Helper to format trend label
        formatTrend(trend) {
            if (!trend) return '-';
            return trend.charAt(0).toUpperCase() + trend.slice(1).replace('_', ' ');
        },

        // === ALPHA COMPUTED ===

        get alphaCompanies() {
            return this.alpha.companies || [];
        },

        get currentAlphaAnalysis() {
            if (!this.selectedAlphaCompany) return null;
            return this.alpha.analyses[this.selectedAlphaCompany] || null;
        },

        get currentAlphaHistory() {
            if (!this.selectedAlphaCompany) return [];
            return this.alpha.history[this.selectedAlphaCompany] || [];
        },

        // Get verdict color class
        getVerdictClass(recommendation) {
            const rec = (recommendation || '').toUpperCase();
            if (rec === 'KÖPVÄRD' || rec === 'KOPVARD') return 'bg-green-600 text-white';
            if (rec === 'ATTRAKTIV') return 'bg-green-500 text-white';
            if (rec === 'FAIR') return 'bg-yellow-500 text-white';
            if (rec === 'FULLVÄRDERAD' || rec === 'FULLVARDERAD') return 'bg-orange-500 text-white';
            if (rec === 'ÖVERVÄRDERAD' || rec === 'OVERVARDERAD') return 'bg-red-600 text-white';
            return 'bg-gray-500 text-white';
        },

        // Get card border color based on verdict
        getCardBorderClass(recommendation) {
            const rec = (recommendation || '').toUpperCase();
            if (rec === 'KÖPVÄRD' || rec === 'KOPVARD') return 'border-green-500';
            if (rec === 'ATTRAKTIV') return 'border-green-400';
            if (rec === 'FAIR') return 'border-yellow-400';
            if (rec === 'FULLVÄRDERAD' || rec === 'FULLVARDERAD') return 'border-orange-400';
            if (rec === 'ÖVERVÄRDERAD' || rec === 'OVERVARDERAD') return 'border-red-500';
            return 'border-gray-300';
        },

        // Get upside color class
        getUpsideClass(upside) {
            if (upside === null || upside === undefined) return 'text-gray-500';
            if (upside > 20) return 'text-green-600 font-bold';
            if (upside > 5) return 'text-green-500';
            if (upside > -10) return 'text-yellow-600';
            if (upside > -20) return 'text-orange-500';
            return 'text-red-600 font-bold';
        },

        // Get risk score color
        getRiskScoreClass(score) {
            if (!score) return 'bg-gray-200 text-gray-600';
            if (score <= 3) return 'bg-green-100 text-green-800';
            if (score <= 5) return 'bg-yellow-100 text-yellow-800';
            if (score <= 7) return 'bg-orange-100 text-orange-800';
            return 'bg-red-100 text-red-800';
        },

        // Get quality score color
        getQualityScoreClass(score) {
            if (!score) return 'bg-gray-200 text-gray-600';
            if (score >= 8) return 'bg-green-100 text-green-800';
            if (score >= 6) return 'bg-yellow-100 text-yellow-800';
            if (score >= 4) return 'bg-orange-100 text-orange-800';
            return 'bg-red-100 text-red-800';
        },

        // Get insider direction class
        getInsiderClass(direction) {
            const dir = (direction || '').toLowerCase();
            if (dir.includes('köp') || dir.includes('buyer') || dir === 'stark_köpare') return 'text-green-600';
            if (dir.includes('sälj') || dir.includes('seller')) return 'text-red-600';
            return 'text-gray-500';
        },

        // Calculate price position as percentage between bear and bull case
        getAlphaPricePosition(analysis) {
            if (!analysis || !analysis.scenarios) return 50;
            const scenarios = analysis.scenarios;
            const bear = scenarios.find(s => s.name === 'Bear');
            const bull = scenarios.find(s => s.name === 'Bull');
            if (!bear || !bull) return 50;

            const price = analysis.current_price;
            const bearFv = bear.fair_value;
            const bullFv = bull.fair_value;

            if (!price || !bearFv || !bullFv) return 50;
            if (bullFv === bearFv) return 50;

            // Calculate position (0 = at bear, 100 = at bull)
            const position = ((price - bearFv) / (bullFv - bearFv)) * 100;
            return Math.max(0, Math.min(100, position));
        },

        // Format currency for Swedish display
        formatSEK(value) {
            if (value === null || value === undefined) return '-';
            return `${value.toFixed(0)} SEK`;
        },

        // Format percentage
        formatPercent(value) {
            if (value === null || value === undefined) return '-';
            const prefix = value >= 0 ? '+' : '';
            return `${prefix}${value.toFixed(1)}%`;
        },

        // === INITIALIZATION ===

        async init() {
            try {
                // Check for inline data first (embedded by generator to avoid CORS issues)
                if (window.DASHBOARD_DATA) {
                    this.loadSource = 'inline';
                    const data = window.DASHBOARD_DATA;
                    this.metadata = data.metadata || {};
                    this.analyses = data.analyses || [];
                    this.recommendations = data.recommendations || [];
                    this.sources = data.sources || [];

                    // Load source-specific data
                    this.podcasts = data.podcasts || { episodes: [], sources: [], stock_mentions: [] };
                    this.twitter = data.twitter || { tweets: [], users: [], stock_mentions: [] };
                    this.youtube = data.youtube || { videos: [], channels: [], stock_mentions: [] };
                    this.filings = data.filings || { companies: [], evolutions: {}, theses: {} };
                    this.alpha = data.alpha || { companies: [], analyses: {}, history: {} };

                    // Set default selected company if available
                    if (this.filings.companies.length > 0) {
                        this.selectedFilingCompany = this.filings.companies[0];
                    }
                    if (this.alpha.companies.length > 0) {
                        this.selectedAlphaCompany = this.alpha.companies[0].ticker;
                    }
                } else {
                    // Fallback to fetch (works when served via HTTP)
                    this.loadSource = 'fetch';
                    const [
                        metadata,
                        analyses,
                        recommendations,
                        sources,
                        podcasts,
                        twitter,
                        youtube,
                        filings,
                        alpha
                    ] = await Promise.all([
                        this.loadJson('data/metadata.json'),
                        this.loadJson('data/analyses.json'),
                        this.loadJson('data/recommendations.json'),
                        this.loadJson('data/sources.json'),
                        this.loadJson('data/podcasts.json'),
                        this.loadJson('data/twitter.json'),
                        this.loadJson('data/youtube.json'),
                        this.loadJson('data/filings.json'),
                        this.loadJson('data/alpha.json'),
                    ]);

                    this.metadata = metadata || {};
                    this.analyses = analyses || [];
                    this.recommendations = recommendations || [];
                    this.sources = sources || [];
                    this.podcasts = podcasts || { episodes: [], sources: [], stock_mentions: [] };
                    this.twitter = twitter || { tweets: [], users: [], stock_mentions: [] };
                    this.youtube = youtube || { videos: [], channels: [], stock_mentions: [] };
                    this.filings = filings || { companies: [], evolutions: {}, theses: {} };
                    this.alpha = alpha || { companies: [], analyses: {}, history: {} };

                    // Set default selected company if available
                    if (this.filings.companies.length > 0) {
                        this.selectedFilingCompany = this.filings.companies[0];
                    }
                    if (this.alpha.companies.length > 0) {
                        this.selectedAlphaCompany = this.alpha.companies[0].ticker;
                    }
                }

            } catch (error) {
                console.error('Error loading dashboard data:', error);
                this.loadErrors.push({ type: 'init', error: error.message });
            } finally {
                this.loading = false;
            }
        },

        async loadJson(path, retries = 2) {
            for (let attempt = 0; attempt <= retries; attempt++) {
                try {
                    const response = await fetch(path);
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return await response.json();
                } catch (error) {
                    if (attempt === retries) {
                        console.warn(`Failed to load ${path} after ${retries + 1} attempts:`, error);
                        this.loadErrors.push({ file: path, error: error.message });
                        return null;
                    }
                    // Wait before retry (1s, 2s, etc.)
                    await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
                }
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
        },

        // === PODCAST FILTER HELPERS ===

        // Convert date preset to actual date range
        getPodcastDateRange() {
            const preset = this.podcastFilters.datePreset;
            if (!preset) {
                // Use custom dates if no preset
                return {
                    from: this.podcastFilters.dateFrom,
                    to: this.podcastFilters.dateTo
                };
            }

            const now = new Date();
            let from = null;
            const to = now.toISOString().split('T')[0]; // Today

            switch (preset) {
                case '7d':
                    from = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                    break;
                case '30d':
                    from = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                    break;
                case '90d':
                    from = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
                    break;
                case 'ytd':
                    from = new Date(now.getFullYear(), 0, 1); // Jan 1 this year
                    break;
            }

            return {
                from: from ? from.toISOString().split('T')[0] : null,
                to: null // No upper bound for presets
            };
        },

        // Filter podcast sources for dropdown search
        get filteredPodcastSources() {
            let sources = this.podcastSources;
            if (this.podcastSourceSearch) {
                const search = this.podcastSourceSearch.toLowerCase();
                sources = sources.filter(s => s.name.toLowerCase().includes(search));
            }
            // Sort by episode count descending
            return sources.sort((a, b) => (b.episode_count || 0) - (a.episode_count || 0));
        },

        // Check if a podcast source is selected
        isPodcastSourceSelected(id) {
            return this.podcastFilters.sources.includes(id);
        },

        // Toggle podcast source selection
        togglePodcastSource(id) {
            const index = this.podcastFilters.sources.indexOf(id);
            if (index === -1) {
                this.podcastFilters.sources.push(id);
            } else {
                this.podcastFilters.sources.splice(index, 1);
            }
        },

        // Remove podcast source from selection
        removePodcastSource(id) {
            const index = this.podcastFilters.sources.indexOf(id);
            if (index !== -1) {
                this.podcastFilters.sources.splice(index, 1);
            }
        },

        // Get podcast source name by ID
        getPodcastSourceName(id) {
            const source = this.podcastSources.find(s => s.id === id);
            return source ? source.name : id;
        },

        // Select all podcast sources
        selectAllPodcastSources() {
            this.podcastFilters.sources = this.filteredPodcastSources.map(s => s.id);
        },

        // Clear podcast source selection
        clearPodcastSourceSelection() {
            this.podcastFilters.sources = [];
        },

        // Set date preset (clears custom dates)
        setPodcastDatePreset(preset) {
            this.podcastFilters.datePreset = preset;
            this.podcastFilters.dateFrom = '';
            this.podcastFilters.dateTo = '';
        },

        // Set custom date (clears preset)
        setPodcastCustomDate(field, value) {
            this.podcastFilters.datePreset = '';
            this.podcastFilters[field] = value;
        },

        // Clear all podcast filters
        clearPodcastFilters() {
            this.podcastFilters = {
                sources: [],
                datePreset: '',
                dateFrom: '',
                dateTo: '',
                companySearch: '',
                positionDisclosure: '',
                action: '',
                confidence: '',
                hasPriceTarget: false,
            };
            this.podcastSourceSearch = '';
        },

        // Apply quick filter (preserves sources)
        applyPodcastQuickFilter(preset) {
            const sources = [...this.podcastFilters.sources]; // Preserve sources

            switch (preset) {
                case 'highConviction':
                    this.podcastFilters = {
                        sources: sources,
                        datePreset: '30d',
                        dateFrom: '',
                        dateTo: '',
                        companySearch: '',
                        positionDisclosure: '',
                        action: '',
                        confidence: 'high',
                        hasPriceTarget: false,
                    };
                    break;
                case 'buyOnly':
                    this.podcastFilters = {
                        sources: sources,
                        datePreset: '',
                        dateFrom: '',
                        dateTo: '',
                        companySearch: '',
                        positionDisclosure: '',
                        action: 'buy',
                        confidence: '',
                        hasPriceTarget: false,
                    };
                    break;
                case 'withPriceTarget':
                    this.podcastFilters = {
                        sources: sources,
                        datePreset: '',
                        dateFrom: '',
                        dateTo: '',
                        companySearch: '',
                        positionDisclosure: '',
                        action: '',
                        confidence: '',
                        hasPriceTarget: true,
                    };
                    break;
            }
        }
    };
}
