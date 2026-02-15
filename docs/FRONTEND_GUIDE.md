# Frontend Integration Guide

Complete guide for the AI Betting Analysis System web interface.

## 🎯 Overview

The frontend is a modern React application that provides a beautiful, real-time interface for viewing AI-powered betting recommendations. It connects to the FastAPI backend and displays the top 3 betting opportunities with detailed analytics.

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         React Frontend (Port 3000)       │
│                                          │
│  ┌────────────┐      ┌──────────────┐  │
│  │  App.jsx   │──────│  BetCard.jsx │  │
│  └────────────┘      └──────────────┘  │
│         │                                │
│         ▼                                │
│  ┌────────────┐                         │
│  │ api.js     │                         │
│  │ (Axios)    │                         │
│  └────────────┘                         │
└─────────────────────────────────────────┘
         │
         │ HTTP/REST
         ▼
┌─────────────────────────────────────────┐
│      FastAPI Backend (Port 8000)        │
│                                          │
│  /api/v1/betting/top3                   │
│  /api/v1/betting/events                 │
│  /api/v1/crypto/balance                 │
│  /api/v1/betting/stats/summary          │
└─────────────────────────────────────────┘
```

## 🚀 Setup Instructions

### Step 1: Install Dependencies

```bash
cd frontend
npm install
```

This installs:
- React 18.2.0
- Vite 5.0.11 (build tool)
- Tailwind CSS 3.4.1
- Axios 1.6.5 (HTTP client)
- Lucide React (icons)
- date-fns (date formatting)

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
VITE_API_URL=http://localhost:8000
VITE_ENV=development
```

### Step 3: Start Backend API

Ensure the backend is running:
```bash
# In the root directory
docker-compose up -d
# OR
uvicorn src.api.main:app --reload
```

Verify backend is accessible:
```bash
curl http://localhost:8000/health
```

### Step 4: Start Frontend

```bash
npm run dev
```

Access at: http://localhost:3000

## 📱 User Interface

### Main Dashboard

The dashboard displays:

1. **Header Section**
   - Logo and branding
   - USDT balance (real-time)
   - Refresh button
   - Auto-refresh toggle

2. **Statistics Bar**
   - Total bets placed
   - Win rate percentage
   - Won bets count
   - Pending bets count

3. **Top 3 Recommendations**
   - Ranked betting opportunities
   - Detailed metrics for each bet
   - One-click bet placement

4. **Information Footer**
   - How the system works
   - Responsible betting reminder

### Bet Card Components

Each recommendation card shows:

#### Header
- 🥇/🥈/🥉 Rank badge
- Sport category badge
- Event start time
- Event name
- Selection and odds

#### Metrics Grid
- **Confidence Score**: 0-100% with color coding
  - 80%+ = Green (high confidence)
  - 70-79% = Blue (good confidence)
  - 60-69% = Yellow (moderate)
  - <60% = Red (low)

- **Expected Value**: Percentage above fair odds
  - Shows mathematical edge
  - Positive EV required for display

- **Win Probability**: Model's predicted chance
  - Based on ensemble predictions
  - Compared to implied probability

- **Risk Score**: Uncertainty measure
  - Lower is better
  - 0-30% = Low risk (green)
  - 31-50% = Medium risk (yellow)
  - 51%+ = High risk (red)

#### Stake Recommendation
- Dollar amount to bet
- Percentage of bankroll
- Calculated using Kelly Criterion
- "Place Bet" button

#### Analysis Section
- Summary of recommendation
- Key reasons (bullet points)
- Value analysis breakdown
  - Model probability vs implied
  - Edge over market odds

## 🔌 API Integration

### API Service (`src/services/api.js`)

The frontend uses Axios for all API calls:

```javascript
import { bettingAPI, cryptoAPI, systemAPI } from './services/api';

// Get top 3 recommendations
const data = await bettingAPI.getTop3Bets();

// Get wallet balance
const balance = await cryptoAPI.getBalance('USDT');

// Get betting statistics
const stats = await bettingAPI.getBettingStats();
```

### Request Flow

1. User opens dashboard
2. Frontend makes parallel API calls:
   - `GET /api/v1/betting/top3`
   - `POST /api/v1/crypto/balance`
   - `GET /api/v1/betting/stats/summary`
3. Data is displayed in real-time
4. Auto-refresh every 60 seconds (if enabled)

### Error Handling

```javascript
try {
  const data = await bettingAPI.getTop3Bets();
  setRecommendations(data.recommendations);
} catch (error) {
  setError(error.response?.data?.detail || 'Failed to fetch');
  console.error('Error:', error);
}
```

## 🎨 Styling System

### Tailwind CSS

The app uses Tailwind CSS with custom configuration:

#### Custom Colors
```javascript
primary: {
  500: '#0ea5e9',  // Main blue
  600: '#0284c7',  // Darker blue
}
success: {
  500: '#22c55e',  // Green
  600: '#16a34a',
}
warning: {
  500: '#f59e0b',  // Yellow
  600: '#d97706',
}
danger: {
  500: '#ef4444',  // Red
  600: '#dc2626',
}
```

#### Utility Classes
```css
.card          /* White card with shadow */
.btn           /* Button base */
.btn-primary   /* Primary blue button */
.btn-success   /* Green button */
.badge         /* Small label/tag */
.stat-card     /* Statistics card */
```

### Responsive Design

```jsx
// Mobile-first approach
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* Responsive grid */}
</div>
```

Breakpoints:
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px

## 🔄 Real-Time Updates

### Auto-Refresh Mechanism

```javascript
useEffect(() => {
  if (!autoRefresh) return;

  const interval = setInterval(() => {
    fetchRecommendations();
    fetchBalance();
    fetchStats();
  }, 60000); // 60 seconds

  return () => clearInterval(interval);
}, [autoRefresh]);
```

### Live Indicator

```jsx
<div className="relative">
  <div className="w-3 h-3 bg-success-500 rounded-full pulse-ring"></div>
  <div className="absolute inset-0 w-3 h-3 bg-success-500 rounded-full animate-ping"></div>
</div>
```

## 🎯 Component Breakdown

### App.jsx (Main Component)

**State Management:**
```javascript
const [recommendations, setRecommendations] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);
const [balance, setBalance] = useState(null);
const [stats, setStats] = useState(null);
const [lastUpdate, setLastUpdate] = useState(null);
const [autoRefresh, setAutoRefresh] = useState(true);
```

**Key Functions:**
- `fetchRecommendations()`: Get top 3 bets
- `fetchBalance()`: Get wallet balance
- `fetchStats()`: Get betting statistics
- `handleRefresh()`: Manual refresh
- `handlePlaceBet()`: Bet placement handler

### BetCard.jsx (Bet Display)

**Props:**
```javascript
{
  bet: {
    event_name,
    sport,
    start_time,
    selection,
    recommended_odds,
    confidence_score,
    expected_value,
    risk_score,
    recommended_stake,
    rationale
  },
  rank: 1-3,
  onPlaceBet: function
}
```

**Features:**
- Rank badge with emoji
- Color-coded metrics
- Expandable analysis
- Hover effects
- Responsive layout

## 🚀 Production Deployment

### Build for Production

```bash
npm run build
```

Output: `dist/` directory

### Serve Static Files

#### Option 1: Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    root /path/to/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Option 2: Docker

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Environment Variables

Production `.env`:
```env
VITE_API_URL=https://api.yourdomain.com
VITE_ENV=production
```

## 🐛 Troubleshooting

### Issue: API Connection Failed

**Symptoms:**
- Error message: "Failed to fetch recommendations"
- Network errors in console

**Solutions:**
1. Check backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verify CORS settings in `config/config.yaml`:
   ```yaml
   api:
     cors:
       enabled: true
       origins:
         - "http://localhost:3000"
   ```

3. Check `.env` file:
   ```env
   VITE_API_URL=http://localhost:8000
   ```

### Issue: Blank Page

**Symptoms:**
- White screen
- No errors in console

**Solutions:**
1. Check browser console for errors
2. Verify all dependencies installed:
   ```bash
   rm -rf node_modules
   npm install
   ```
3. Clear Vite cache:
   ```bash
   rm -rf node_modules/.vite
   ```

### Issue: Styling Not Applied

**Symptoms:**
- Unstyled components
- Missing Tailwind classes

**Solutions:**
1. Verify Tailwind config:
   ```bash
   cat tailwind.config.js
   ```

2. Check PostCSS config:
   ```bash
   cat postcss.config.js
   ```

3. Rebuild:
   ```bash
   npm run build
   ```

### Issue: Auto-Refresh Not Working

**Symptoms:**
- Data doesn't update automatically
- Toggle doesn't work

**Solutions:**
1. Check auto-refresh is enabled (toggle in header)
2. Verify interval is set correctly (60 seconds)
3. Check browser console for errors
4. Ensure backend is responding

## 📊 Performance Optimization

### Code Splitting

Vite automatically splits code for optimal loading.

### Lazy Loading

For future pages:
```javascript
const Dashboard = lazy(() => import('./pages/Dashboard'));
```

### Memoization

For expensive calculations:
```javascript
const memoizedValue = useMemo(() => {
  return expensiveCalculation(data);
}, [data]);
```

### Debouncing

For search/filter inputs:
```javascript
const debouncedSearch = debounce((value) => {
  performSearch(value);
}, 300);
```

## 🔐 Security Best Practices

1. **Never expose API keys in frontend**
   - Use environment variables
   - Keep sensitive data in backend

2. **Validate user input**
   - Sanitize before sending to API
   - Use proper form validation

3. **Implement authentication**
   - JWT tokens
   - Secure storage (httpOnly cookies)

4. **HTTPS in production**
   - Always use SSL/TLS
   - Secure cookie flags

## 📈 Future Enhancements

### Phase 1: Enhanced UI
- [ ] Dark mode toggle
- [ ] Custom themes
- [ ] Animations and transitions
- [ ] Loading skeletons

### Phase 2: Advanced Features
- [ ] Bet placement modal
- [ ] Historical charts (Recharts)
- [ ] Live odds comparison
- [ ] Arbitrage opportunities view

### Phase 3: User Features
- [ ] User authentication
- [ ] Betting history
- [ ] Custom filters
- [ ] Saved preferences

### Phase 4: Mobile
- [ ] Progressive Web App (PWA)
- [ ] Push notifications
- [ ] Offline support
- [ ] Native app wrapper

## 📚 Additional Resources

- [React Documentation](https://react.dev)
- [Vite Guide](https://vitejs.dev/guide/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Axios Documentation](https://axios-http.com/docs/intro)

---

**Frontend successfully integrated with AI Betting Analysis System! 🎉**
