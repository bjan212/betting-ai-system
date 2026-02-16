import React from 'react';
import { TrendingUp, Target, DollarSign, AlertCircle, CheckCircle, Clock, ExternalLink } from 'lucide-react';
import { format } from 'date-fns';

const BetCard = ({ bet, rank, onPlaceBet, placingBet = false }) => {
  const {
    event_name,
    sport,
    start_time,
    selection,
    recommended_odds,
    bookmaker,
    confidence_score,
    expected_value,
    risk_score,
    probability,
    recommended_stake,
    recommended_stake_percentage,
    rationale,
    bet_link
  } = bet;

  const getConfidenceColor = (score) => {
    if (score >= 80) return 'text-success-600 bg-success-50';
    if (score >= 70) return 'text-primary-600 bg-primary-50';
    if (score >= 60) return 'text-warning-600 bg-warning-50';
    return 'text-danger-600 bg-danger-50';
  };

  const getRiskColor = (score) => {
    if (score <= 0.3) return 'text-success-600';
    if (score <= 0.5) return 'text-warning-600';
    return 'text-danger-600';
  };

  const getRankBadge = (rank) => {
    const badges = {
      1: { bg: 'bg-gradient-to-r from-yellow-400 to-yellow-600', text: '🥇 #1 BEST BET' },
      2: { bg: 'bg-gradient-to-r from-gray-300 to-gray-500', text: '🥈 #2' },
      3: { bg: 'bg-gradient-to-r from-orange-400 to-orange-600', text: '🥉 #3' }
    };
    return badges[rank] || { bg: 'bg-gray-500', text: `#${rank}` };
  };

  const rankBadge = getRankBadge(rank);

  return (
    <div className="card relative overflow-hidden group hover:scale-[1.02] transition-transform duration-200">
      {/* Rank Badge */}
      <div className={`absolute top-0 right-0 ${rankBadge.bg} text-white px-4 py-2 rounded-bl-lg font-bold text-sm shadow-lg`}>
        {rankBadge.text}
      </div>

      {/* Header */}
      <div className="mb-4 pr-24">
        <div className="flex items-center gap-2 mb-2">
          <span className="badge badge-primary">{sport}</span>
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {format(new Date(start_time), 'MMM dd, HH:mm')}
          </span>
        </div>
        <h3 className="text-xl font-bold text-gray-900 mb-1">{event_name}</h3>
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold text-primary-600">{selection}</span>
          <span className="text-gray-400">@</span>
          <span className="text-lg font-bold text-gray-900">{recommended_odds.toFixed(2)}</span>
          <span className="text-xs text-gray-500">({bookmaker})</span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        {/* Confidence */}
        <div className={`p-3 rounded-lg ${getConfidenceColor(confidence_score)}`}>
          <div className="flex items-center gap-2 mb-1">
            <Target className="w-4 h-4" />
            <span className="text-xs font-medium">Confidence</span>
          </div>
          <div className="text-2xl font-bold">{confidence_score.toFixed(1)}%</div>
        </div>

        {/* Expected Value */}
        <div className="p-3 rounded-lg bg-success-50 text-success-600">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4" />
            <span className="text-xs font-medium">Expected Value</span>
          </div>
          <div className="text-2xl font-bold">+{(expected_value * 100).toFixed(1)}%</div>
        </div>

        {/* Win Probability */}
        <div className="p-3 rounded-lg bg-primary-50 text-primary-600">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle className="w-4 h-4" />
            <span className="text-xs font-medium">Win Probability</span>
          </div>
          <div className="text-2xl font-bold">{(probability * 100).toFixed(1)}%</div>
        </div>

        {/* Risk Score */}
        <div className="p-3 rounded-lg bg-gray-50">
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle className={`w-4 h-4 ${getRiskColor(risk_score)}`} />
            <span className="text-xs font-medium text-gray-600">Risk Score</span>
          </div>
          <div className={`text-2xl font-bold ${getRiskColor(risk_score)}`}>
            {(risk_score * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Stake Recommendation */}
      <div className="bg-gradient-to-r from-primary-50 to-primary-100 p-4 rounded-lg mb-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="w-5 h-5 text-primary-600" />
              <span className="text-sm font-medium text-gray-700">Tiered Stake</span>
            </div>
            <div className="text-3xl font-bold text-primary-600">
              ${recommended_stake.toFixed(2)}
            </div>
            <div className="text-xs text-gray-600 mt-1 flex items-center gap-2">
              <span className="badge badge-primary text-[10px] px-1.5 py-0.5">
                {probability >= 0.90 ? '90-99%' : probability >= 0.80 ? '80-90%' : probability >= 0.70 ? '70-80%' : probability >= 0.60 ? '60-70%' : '<60%'} tier
              </span>
              <span>{recommended_stake_percentage.toFixed(1)}% of bankroll</span>
            </div>
          </div>
          <button
            onClick={() => onPlaceBet(bet)}
            disabled={placingBet}
            className="btn btn-primary px-6 py-3 text-lg font-bold shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all disabled:opacity-60 flex items-center gap-2"
          >
            <ExternalLink className="w-5 h-5" />
            {placingBet ? 'Opening...' : bet_link?.bookmaker_display ? `Bet $${recommended_stake.toFixed(0)} at ${bet_link.bookmaker_display}` : 'Place Bet'}
          </button>
        </div>
      </div>

      {/* Rationale */}
      <div className="border-t pt-4">
        <h4 className="font-semibold text-gray-900 mb-2">Analysis</h4>
        <p className="text-sm text-gray-700 mb-3">{rationale?.summary}</p>
        
        {rationale?.key_reasons && rationale.key_reasons.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-600 mb-1">Key Reasons:</p>
            {rationale.key_reasons.map((reason, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                <CheckCircle className="w-4 h-4 text-success-500 mt-0.5 flex-shrink-0" />
                <span>{reason}</span>
              </div>
            ))}
          </div>
        )}

        {/* Value Analysis */}
        {rationale?.value_analysis && (
          <div className="mt-3 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs font-medium text-gray-600 mb-2">Value Analysis:</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-500">Model Probability:</span>
                <span className="ml-2 font-semibold text-gray-900">
                  {rationale.value_analysis.model_probability}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Implied Probability:</span>
                <span className="ml-2 font-semibold text-gray-900">
                  {rationale.value_analysis.implied_probability}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-gray-500">Edge vs Market:</span>
                <span className="ml-2 font-semibold text-success-600">
                  {rationale.value_analysis.edge}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Hover Effect Overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-primary-500/0 to-primary-500/0 group-hover:from-primary-500/5 group-hover:to-transparent transition-all duration-300 pointer-events-none rounded-lg" />
    </div>
  );
};

export default BetCard;
