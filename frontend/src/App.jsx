import React, { useState, useEffect } from 'react';
import { TrendingUp, RefreshCw, Activity, Wallet, BarChart3, Settings, ExternalLink, Search } from 'lucide-react';
import BetCard from './components/BetCard';
import { bettingAPI, cryptoAPI, systemAPI } from './services/api';

function App() {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [balance, setBalance] = useState(null);
  const [stats, setStats] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showPolymarketSettings, setShowPolymarketSettings] = useState(false);
  const [savingPolymarketSettings, setSavingPolymarketSettings] = useState(false);
  const [placingBet, setPlacingBet] = useState(false);
  const [showBetConfirm, setShowBetConfirm] = useState(false);
  const [pendingBet, setPendingBet] = useState(null);
  const [polymarketStatus, setPolymarketStatus] = useState(null);
  const [polymarketBalance, setPolymarketBalance] = useState(null);
  const [polymarketBalanceError, setPolymarketBalanceError] = useState(null);
  const [polymarketMarkets, setPolymarketMarkets] = useState([]);
  const [polymarketMarketsLoading, setPolymarketMarketsLoading] = useState(false);
  const [polymarketSearch, setPolymarketSearch] = useState('');
  const [polymarketConfig, setPolymarketConfig] = useState({
    privateKey: '',
    funderAddress: '',
    signatureType: 0,
    defaultCurrency: 'USDC',
  });

  // Fetch top 3 recommendations
  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await bettingAPI.getTop3Bets();
      setRecommendations(data.recommendations || []);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch recommendations');
      console.error('Error fetching recommendations:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch wallet balance
  const fetchBalance = async () => {
    try {
      const data = await cryptoAPI.getBalance('USDT');
      setBalance(data);
    } catch (err) {
      console.error('Error fetching balance:', err);
    }
  };

  // Fetch betting stats
  const fetchStats = async () => {
    try {
      const data = await bettingAPI.getBettingStats();
      setStats(data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  // Initial load
  useEffect(() => {
    fetchRecommendations();
    fetchBalance();
    fetchStats();
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem('polymarket_config');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setPolymarketConfig((prev) => ({ ...prev, ...parsed }));
        if (parsed.privateKey) {
          bettingAPI.updatePolymarketConfig({
            privateKey: parsed.privateKey,
            funderAddress: parsed.funderAddress || null,
            signatureType: parsed.signatureType || 0,
          }).then(() => {
            fetchPolymarketBalance();
          }).catch((err) => {
            console.error('Polymarket config restore failed:', err);
          });
        }
      } catch (err) {
        console.error('Failed to parse polymarket config:', err);
      }
    }
  }, []);

  const fetchPolymarketBalance = async () => {
    try {
      setPolymarketBalanceError(null);
      const data = await bettingAPI.getPolymarketBalance();
      setPolymarketBalance(data);
      if (data.connected) {
        setPolymarketStatus({
          type: 'success',
          message: data.message || 'Polymarket connected'
        });
      } else if (data.credentials_saved) {
        // API unreachable but credentials are saved (e.g. US geo-restriction)
        setPolymarketStatus({
          type: 'warning',
          message: data.message || 'Credentials saved. Polymarket API unreachable (US geo-restriction). Use VPN for live access.'
        });
      } else {
        setPolymarketStatus({
          type: 'error',
          message: data.message || 'Polymarket connection failed'
        });
      }
    } catch (err) {
      setPolymarketBalance(null);
      setPolymarketBalanceError(err.response?.data?.detail || 'Failed to fetch Polymarket balance');
      setPolymarketStatus({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to fetch Polymarket balance'
      });
    }
  };

  // Auto-refresh every 60 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchRecommendations();
      fetchBalance();
      fetchStats();
    }, 60000); // 60 seconds

    return () => clearInterval(interval);
  }, [autoRefresh]);

  // Tiered stake calculation (mirrors backend)
  const getTieredStake = (probability) => {
    if (probability >= 0.90) return { amount: 22, tier: '90-99%' };
    if (probability >= 0.80) return { amount: 5, tier: '80-90%' };
    if (probability >= 0.70) return { amount: 3, tier: '70-80%' };
    if (probability >= 0.60) return { amount: 1, tier: '60-70%' };
    return { amount: 0, tier: 'below threshold' };
  };

  // Handle place bet (for top-3 sportsbook recommendations)
  const handlePlaceBet = (bet) => {
    setPendingBet({ ...bet, _source: 'sportsbook' });
    setShowBetConfirm(true);
  };

  // Handle place bet for Polymarket futures
  const handlePlacePolymarketBet = (market, token) => {
    const stake = getTieredStake(token.price);
    setPendingBet({
      _source: 'polymarket',
      event_name: market.question,
      selection: token.outcome,
      recommended_odds: (1 / token.price).toFixed(2),
      recommended_stake: stake.amount,
      probability: token.price,
      bookmaker: 'Polymarket',
      token_id: token.token_id,
      market_price: token.price,
      question: market.question,
      url: market.url,
      tier: stake.tier,
    });
    setShowBetConfirm(true);
  };

  const handleConfirmBet = async () => {
    if (!pendingBet) return;

    try {
      setPlacingBet(true);

      if (pendingBet._source === 'polymarket' && pendingBet.token_id) {
        // Direct Polymarket placement via API
        const result = await bettingAPI.directBet({
          tokenId: pendingBet.token_id,
          outcome: pendingBet.selection,
          marketPrice: pendingBet.market_price,
          question: pendingBet.question,
        });
        alert(
          `Bet placed on Polymarket!\n` +
          `Outcome: ${result.outcome}\n` +
          `Stake: $${result.stake} (${result.tier} tier)\n` +
          `Order ID: ${result.order_id || 'N/A'}`
        );
      } else {
        // Sportsbook redirect
        const url = pendingBet.bet_link?.search_url || pendingBet.bet_link?.url;
        if (url) {
          window.open(url, '_blank', 'noopener,noreferrer');
        } else {
          alert('No sportsbook link available for this bet.');
        }
      }

      setShowBetConfirm(false);
      setPendingBet(null);
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to place bet';
      alert(detail);
      console.error('Error placing bet:', err);
    } finally {
      setPlacingBet(false);
    }
  };

  const handleSavePolymarketSettings = async () => {
    try {
      setSavingPolymarketSettings(true);
      const result = await bettingAPI.updatePolymarketConfig({
        privateKey: polymarketConfig.privateKey,
        funderAddress: polymarketConfig.funderAddress || null,
        signatureType: polymarketConfig.signatureType,
      });
      localStorage.setItem('polymarket_config', JSON.stringify(polymarketConfig));

      if (result.warning) {
        // API unreachable (e.g. US geo-restriction) but credentials saved
        setPolymarketStatus({
          type: 'warning',
          message: result.warning
        });
        setShowPolymarketSettings(false);
      } else {
        await fetchPolymarketBalance();
        setShowPolymarketSettings(false);
      }
    } catch (err) {
      setPolymarketStatus({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to save Polymarket settings'
      });
      alert(err.response?.data?.detail || 'Failed to save Polymarket settings');
      console.error('Error saving Polymarket settings:', err);
    } finally {
      setSavingPolymarketSettings(false);
    }
  };

  // Manual refresh
  const handleRefresh = () => {
    fetchRecommendations();
    fetchBalance();
    fetchStats();
  };

  // Fetch Polymarket sports futures markets
  const fetchPolymarketMarkets = async (query = null) => {
    try {
      setPolymarketMarketsLoading(true);
      const data = await bettingAPI.getPolymarketSports(query);
      setPolymarketMarkets(data.markets || []);
    } catch (err) {
      console.error('Error fetching Polymarket markets:', err);
    } finally {
      setPolymarketMarketsLoading(false);
    }
  };

  const handlePolymarketSearch = (e) => {
    e.preventDefault();
    fetchPolymarketMarkets(polymarketSearch || null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-br from-primary-500 to-primary-700 p-2 rounded-lg">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold gradient-text">AI Betting Analysis</h1>
                <p className="text-sm text-gray-500">Smart Betting Decisions</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {polymarketBalance && !polymarketBalanceError && (
                <div className="flex items-center gap-2 bg-primary-50 px-4 py-2 rounded-lg">
                  <div>
                    <div className="text-xs text-gray-600">Polymarket Status</div>
                    <div className="font-bold text-primary-700">
                      {polymarketBalance.connected ? 'Connected' : 'Disconnected'}
                    </div>
                  </div>
                </div>
              )}
              {/* Balance */}
              {balance && (
                <div className="flex items-center gap-2 bg-success-50 px-4 py-2 rounded-lg">
                  <Wallet className="w-5 h-5 text-success-600" />
                  <div>
                    <div className="text-xs text-gray-600">Balance</div>
                    <div className="font-bold text-success-600">
                      ${balance.balance?.toFixed(2) || '0.00'} USDT
                    </div>
                  </div>
                </div>
              )}

              {/* Refresh Button */}
              <button
                onClick={handleRefresh}
                disabled={loading}
                className="btn btn-secondary flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>

              <button
                onClick={() => setShowPolymarketSettings(true)}
                className="btn btn-secondary flex items-center gap-2"
              >
                <Settings className="w-4 h-4" />
                Polymarket Settings
              </button>

              {/* Auto-refresh Toggle */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-600">Auto-refresh</span>
              </label>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {polymarketStatus && (
          <div
            className={`mb-6 rounded-lg border px-4 py-3 text-sm ${
              polymarketStatus.type === 'success'
                ? 'bg-success-50 border-success-200 text-success-700'
                : polymarketStatus.type === 'warning'
                ? 'bg-yellow-50 border-yellow-200 text-yellow-700'
                : 'bg-danger-50 border-danger-200 text-danger-700'
            }`}
          >
            {polymarketStatus.message}
          </div>
        )}
        {/* Stats Bar */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Total Bets</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.total_recommendations}</p>
                </div>
                <BarChart3 className="w-8 h-8 text-primary-500" />
              </div>
            </div>

            <div className="stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Win Rate</p>
                  <p className="text-2xl font-bold text-success-600">{stats.win_rate?.toFixed(1)}%</p>
                </div>
                <Activity className="w-8 h-8 text-success-500" />
              </div>
            </div>

            <div className="stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Won Bets</p>
                  <p className="text-2xl font-bold text-success-600">{stats.won_bets}</p>
                </div>
                <div className="text-3xl">✅</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Pending</p>
                  <p className="text-2xl font-bold text-warning-600">{stats.pending_bets}</p>
                </div>
                <div className="text-3xl">⏳</div>
              </div>
            </div>
          </div>
        )}

        {/* Title Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                🎯 Top 3 Betting Opportunities
              </h2>
              <p className="text-gray-600">
                AI-powered recommendations for the next 24 hours
              </p>
            </div>
            {lastUpdate && (
              <div className="text-sm text-gray-500">
                Last updated: {lastUpdate.toLocaleTimeString()}
              </div>
            )}
          </div>

          {/* Live Indicator */}
          <div className="flex items-center gap-2 text-sm">
            <div className="relative">
              <div className="w-3 h-3 bg-success-500 rounded-full pulse-ring"></div>
              <div className="absolute inset-0 w-3 h-3 bg-success-500 rounded-full animate-ping"></div>
            </div>
            <span className="text-gray-600">Live recommendations updating every 60 seconds</span>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-danger-50 border border-danger-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-danger-800">
              <Activity className="w-5 h-5" />
              <span className="font-medium">Error: {error}</span>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && recommendations.length === 0 && (
          <div className="space-y-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card skeleton h-96"></div>
            ))}
          </div>
        )}

        {/* Recommendations */}
        {!loading && recommendations.length === 0 && !error && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No recommendations available
            </h3>
            <p className="text-gray-600 mb-4">
              No betting opportunities found that meet our criteria at the moment.
            </p>
            <button onClick={handleRefresh} className="btn btn-primary">
              Refresh Recommendations
            </button>
          </div>
        )}

        {recommendations.length > 0 && (
          <div className="space-y-6">
            {recommendations.map((bet, index) => (
              <BetCard
                key={index}
                bet={bet}
                rank={bet.rank || index + 1}
                onPlaceBet={handlePlaceBet}
                placingBet={placingBet}
              />
            ))}
          </div>
        )}

        {showBetConfirm && pendingBet && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
            <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-gray-900">
                  {pendingBet._source === 'polymarket'
                    ? 'Place Bet on Polymarket'
                    : pendingBet.bet_link?.bookmaker_display
                    ? `Bet at ${pendingBet.bet_link.bookmaker_display}`
                    : 'Place Bet'}
                </h3>
                <button
                  onClick={() => setShowBetConfirm(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              {pendingBet._source === 'polymarket' ? (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-4 text-sm text-purple-800">
                  This will place a <strong>real market order</strong> on Polymarket using USDC from your connected wallet.
                </div>
              ) : (
                <p className="text-sm text-gray-500 mb-4">
                  You'll be redirected to{' '}
                  <strong>{pendingBet.bet_link?.bookmaker_display || pendingBet.bookmaker}</strong>{' '}
                  to place this bet.
                </p>
              )}

              <div className="space-y-3 text-sm text-gray-700">
                <div className="flex items-center justify-between">
                  <span>Event</span>
                  <span className="font-semibold text-gray-900 text-right max-w-[60%]">{pendingBet.event_name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Selection</span>
                  <span className="font-semibold text-gray-900">{pendingBet.selection}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Probability</span>
                  <span className="font-semibold text-gray-900">
                    {((pendingBet.probability || 0) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Tiered Stake</span>
                  <span className="font-bold text-xl text-primary-600">
                    ${pendingBet.recommended_stake?.toFixed(2)}
                  </span>
                </div>
                {pendingBet.tier && (
                  <div className="flex items-center justify-between">
                    <span>Stake Tier</span>
                    <span className="badge badge-primary">{pendingBet.tier}</span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span>Platform</span>
                  <span className="font-semibold text-primary-600">
                    {pendingBet._source === 'polymarket' ? 'Polymarket' : (pendingBet.bet_link?.bookmaker_display || pendingBet.bookmaker)}
                  </span>
                </div>
              </div>

              {/* Stake tier reference */}
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <p className="text-xs font-medium text-gray-600 mb-2">Auto-Stake Tiers:</p>
                <div className="grid grid-cols-4 gap-2 text-xs text-center">
                  <div className={`p-1.5 rounded ${pendingBet.probability >= 0.60 && pendingBet.probability < 0.70 ? 'bg-primary-100 font-bold text-primary-700' : 'bg-white text-gray-600'}`}>
                    60-70%<br/>$1
                  </div>
                  <div className={`p-1.5 rounded ${pendingBet.probability >= 0.70 && pendingBet.probability < 0.80 ? 'bg-primary-100 font-bold text-primary-700' : 'bg-white text-gray-600'}`}>
                    70-80%<br/>$3
                  </div>
                  <div className={`p-1.5 rounded ${pendingBet.probability >= 0.80 && pendingBet.probability < 0.90 ? 'bg-primary-100 font-bold text-primary-700' : 'bg-white text-gray-600'}`}>
                    80-90%<br/>$5
                  </div>
                  <div className={`p-1.5 rounded ${pendingBet.probability >= 0.90 ? 'bg-primary-100 font-bold text-primary-700' : 'bg-white text-gray-600'}`}>
                    90-99%<br/>$22
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={() => setShowBetConfirm(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmBet}
                  disabled={placingBet}
                  className="btn btn-primary flex items-center gap-2"
                >
                  {pendingBet._source === 'polymarket' ? (
                    <>
                      {placingBet ? 'Placing...' : `Place $${pendingBet.recommended_stake?.toFixed(2)} Bet`}
                    </>
                  ) : (
                    <>
                      <ExternalLink className="w-4 h-4" />
                      {placingBet
                        ? 'Opening...'
                        : `Go to ${pendingBet.bet_link?.bookmaker_display || 'Sportsbook'}`}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {showPolymarketSettings && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
            <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-gray-900">Polymarket Settings</h3>
                <button
                  onClick={() => setShowPolymarketSettings(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              <p className="text-sm text-gray-600 mb-4">
                Your private key is stored only in this browser for local use. Polymarket uses Polygon (USDC).
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Polygon Wallet Private Key
                  </label>
                  <input
                    type="password"
                    value={polymarketConfig.privateKey}
                    onChange={(e) => setPolymarketConfig({ ...polymarketConfig, privateKey: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="0x..."
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Your Polygon wallet private key (starts with 0x)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Funder Address (Optional)
                  </label>
                  <input
                    type="text"
                    value={polymarketConfig.funderAddress}
                    onChange={(e) => setPolymarketConfig({ ...polymarketConfig, funderAddress: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="0x... (only for proxy wallets)"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Only needed if using Magic link or proxy wallet
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Signature Type
                  </label>
                  <select
                    value={polymarketConfig.signatureType}
                    onChange={(e) => setPolymarketConfig({ ...polymarketConfig, signatureType: parseInt(e.target.value) })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value={0}>EOA (MetaMask, Hardware Wallet)</option>
                    <option value={1}>Magic/Email Wallet</option>
                    <option value={2}>Proxy Wallet</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={() => setShowPolymarketSettings(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSavePolymarketSettings}
                  disabled={savingPolymarketSettings}
                  className="btn btn-primary"
                >
                  {savingPolymarketSettings ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Polymarket Futures Section */}
        <div className="mt-12 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-1">
                🔮 Polymarket Sports Futures
              </h2>
              <p className="text-gray-600 text-sm">
                Prediction markets for championships, MVPs, and more
              </p>
            </div>
            <button
              onClick={() => fetchPolymarketMarkets()}
              disabled={polymarketMarketsLoading}
              className="btn btn-secondary flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${polymarketMarketsLoading ? 'animate-spin' : ''}`} />
              {polymarketMarkets.length > 0 ? 'Refresh' : 'Load Markets'}
            </button>
          </div>

          {/* Search */}
          {polymarketMarkets.length > 0 && (
            <form onSubmit={handlePolymarketSearch} className="mb-4">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    value={polymarketSearch}
                    onChange={(e) => setPolymarketSearch(e.target.value)}
                    placeholder="Search markets (e.g. NBA, Champions League, World Cup...)"
                    className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 focus:ring-primary-500 focus:border-primary-500 text-sm"
                  />
                </div>
                <button type="submit" className="btn btn-primary px-4 py-2 text-sm">
                  Search
                </button>
                {polymarketSearch && (
                  <button
                    type="button"
                    onClick={() => { setPolymarketSearch(''); fetchPolymarketMarkets(); }}
                    className="btn btn-secondary px-4 py-2 text-sm"
                  >
                    Clear
                  </button>
                )}
              </div>
            </form>
          )}

          {polymarketMarketsLoading && (
            <div className="text-center py-8 text-gray-500">Loading Polymarket futures...</div>
          )}

          {!polymarketMarketsLoading && polymarketMarkets.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {polymarketMarkets.slice(0, 12).map((market, idx) => (
                <div key={idx} className="card hover:shadow-lg transition-shadow">
                  <div className="mb-3">
                    <h4 className="font-semibold text-gray-900 text-sm leading-tight mb-1">
                      {market.question}
                    </h4>
                    {market.event_title && (
                      <span className="text-xs text-gray-500">{market.event_title}</span>
                    )}
                  </div>

                  {/* Top outcomes by price with Place Bet buttons */}
                  {market.tokens && market.tokens.length > 0 && (
                    <div className="space-y-2 mb-3">
                      {market.tokens
                        .filter((t) => t.price > 0.01)
                        .sort((a, b) => b.price - a.price)
                        .slice(0, 5)
                        .map((token, ti) => {
                          const pct = (token.price * 100).toFixed(0);
                          const stake = getTieredStake(token.price);
                          return (
                            <div
                              key={ti}
                              className="flex items-center justify-between text-xs"
                            >
                              <span className="text-gray-700 truncate mr-2">{token.outcome}</span>
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-primary-600 whitespace-nowrap">
                                  {pct}%
                                </span>
                                {stake.amount > 0 && token.token_id && (
                                  <button
                                    onClick={() => handlePlacePolymarketBet(market, token)}
                                    disabled={placingBet}
                                    className="px-2 py-0.5 bg-primary-500 hover:bg-primary-600 text-white rounded text-[10px] font-bold whitespace-nowrap transition-colors disabled:opacity-50"
                                  >
                                    ${stake.amount}
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  )}

                  <div className="flex items-center justify-between">
                    {market.url && (
                      <a
                        href={market.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 font-medium"
                      >
                        View on Polymarket <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {!polymarketMarketsLoading && polymarketMarkets.length > 12 && (
            <div className="text-center mt-4 text-sm text-gray-500">
              Showing 12 of {polymarketMarkets.length} markets. Use search to find specific ones.
            </div>
          )}
        </div>

        {/* Info Footer */}
        <div className="mt-12 p-6 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-semibold text-blue-900 mb-2">ℹ️ How It Works</h3>
          <ul className="space-y-2 text-sm text-blue-800">
            <li>• <strong>AI Analysis:</strong> Our ensemble ML models analyze thousands of data points</li>
            <li>• <strong>Confidence Score:</strong> Higher scores indicate stronger predictions (65%+ minimum)</li>
            <li>• <strong>Expected Value:</strong> Positive EV means the bet has mathematical value</li>
            <li>• <strong>Risk Score:</strong> Lower is better - indicates prediction certainty</li>
            <li>• <strong>Tiered Stakes:</strong> $1 (60-70%) · $3 (70-80%) · $5 (80-90%) · $22 (90-99%)</li>
            <li>• <strong>Sportsbook Bets:</strong> Opens your bookmaker with the match pre-searched</li>
            <li>• <strong>Polymarket Futures:</strong> Place direct bets on championships, MVPs & more (USDC)</li>
          </ul>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-sm text-gray-500">
            <p>⚠️ Bet responsibly. Past performance doesn't guarantee future results.</p>
            <p className="mt-1">AI Betting Analysis System v1.0.0</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
