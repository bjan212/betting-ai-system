import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Betting API
export const bettingAPI = {
  // Get top 3 recommendations
  getTop3Bets: async () => {
    const response = await api.get('/api/v1/betting/top3');
    return response.data;
  },

  // Get upcoming events
  getUpcomingEvents: async (sport = null, limit = 50) => {
    const params = { limit };
    if (sport) params.sport = sport;
    const response = await api.get('/api/v1/betting/events', { params });
    return response.data;
  },

  // Get prediction for event
  getPrediction: async (eventId) => {
    const response = await api.post('/api/v1/betting/predict', { event_id: eventId });
    return response.data;
  },

  // Get recommendation history
  getRecommendationHistory: async (limit = 50) => {
    const response = await api.get('/api/v1/betting/recommendations/history', {
      params: { limit }
    });
    return response.data;
  },

  // Get available sports
  getSports: async () => {
    const response = await api.get('/api/v1/betting/sports');
    return response.data;
  },

  // Get model performance
  getModelPerformance: async () => {
    const response = await api.get('/api/v1/betting/performance/models');
    return response.data;
  },

  // Get betting statistics
  getBettingStats: async () => {
    const response = await api.get('/api/v1/betting/stats/summary');
    return response.data;
  },

  // Place bet via Polymarket
  placeBet: async ({ tokenId, side, amount, price, size }) => {
    const response = await api.post('/api/v1/betting/place-bet', {
      token_id: tokenId,
      side,
      amount,
      price,
      size,
    });
    return response.data;
  },

  // Update Polymarket API credentials at runtime
  updatePolymarketConfig: async ({ privateKey, funderAddress, signatureType }) => {
    const response = await api.post('/api/v1/betting/polymarket-config', {
      private_key: privateKey,
      funder_address: funderAddress,
      signature_type: signatureType,
    });
    return response.data;
  },

  // Get Polymarket balance to confirm connectivity
  getPolymarketBalance: async () => {
    const response = await api.get('/api/v1/betting/polymarket/balance');
    return response.data;
  },
};

// Crypto API
export const cryptoAPI = {
  // Get balance
  getBalance: async (tokenSymbol = 'USDT') => {
    const response = await api.post('/api/v1/crypto/balance', {
      token_symbol: tokenSymbol
    });
    return response.data;
  },

  // Send transaction
  sendTransaction: async (toAddress, amount, tokenSymbol = 'USDT', privateKey) => {
    const response = await api.post('/api/v1/crypto/send', {
      to_address: toAddress,
      amount,
      token_symbol: tokenSymbol,
      private_key: privateKey
    });
    return response.data;
  },

  // Get transaction status
  getTransactionStatus: async (transactionHash) => {
    const response = await api.post('/api/v1/crypto/transaction/status', {
      transaction_hash: transactionHash
    });
    return response.data;
  },

  // Estimate gas
  estimateGas: async (toAddress, amount, tokenSymbol = 'USDT') => {
    const response = await api.post('/api/v1/crypto/gas/estimate', {
      to_address: toAddress,
      amount,
      token_symbol: tokenSymbol
    });
    return response.data;
  },

  // Get wallet info
  getWalletInfo: async () => {
    const response = await api.get('/api/v1/crypto/wallet/info');
    return response.data;
  },

  // Get supported tokens
  getSupportedTokens: async () => {
    const response = await api.get('/api/v1/crypto/tokens');
    return response.data;
  },
};

// System API
export const systemAPI = {
  // Health check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // System status
  getSystemStatus: async () => {
    const response = await api.get('/api/v1/system/status');
    return response.data;
  },
};

export default api;
