# AI Betting Analysis - Frontend

Modern React-based web interface for the AI Betting Analysis System.

## 🎨 Features

- **Real-time Top 3 Recommendations**: Live display of AI-powered betting opportunities
- **Beautiful UI**: Modern, responsive design with Tailwind CSS
- **Live Updates**: Auto-refresh every 60 seconds
- **Detailed Analytics**: Confidence scores, expected value, risk assessment
- **Wallet Integration**: Real-time balance display
- **Performance Stats**: Win rate, total bets, and more
- **One-Click Betting**: Easy bet placement interface

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Create environment file**
```bash
cp .env.example .env
```

4. **Start development server**
```bash
npm run dev
```

5. **Open browser**
```
http://localhost:3000
```

## 📦 Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## 🛠️ Technology Stack

- **React 18**: Modern React with hooks
- **Vite**: Lightning-fast build tool
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API calls
- **Lucide React**: Beautiful icon library
- **Recharts**: Charting library (ready for future use)
- **date-fns**: Date formatting utilities

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/        # React components
│   │   └── BetCard.jsx   # Bet recommendation card
│   ├── pages/            # Page components (future)
│   ├── services/         # API services
│   │   └── api.js        # API client
│   ├── utils/            # Utility functions
│   ├── styles/           # Global styles
│   │   └── index.css     # Tailwind + custom styles
│   ├── App.jsx           # Main app component
│   └── main.jsx          # Entry point
├── public/               # Static assets
├── index.html            # HTML template
├── vite.config.js        # Vite configuration
├── tailwind.config.js    # Tailwind configuration
└── package.json          # Dependencies
```

## 🎯 Key Components

### BetCard Component

Displays individual betting recommendations with:
- Rank badge (🥇 #1, 🥈 #2, 🥉 #3)
- Event details and timing
- Confidence score with color coding
- Expected value calculation
- Win probability
- Risk assessment
- Recommended stake amount
- Detailed analysis and rationale
- One-click bet placement

### App Component

Main application featuring:
- Header with balance and controls
- Performance statistics dashboard
- Live recommendation feed
- Auto-refresh functionality
- Error handling
- Loading states

## 🔌 API Integration

The frontend connects to the backend API at `http://localhost:8000` (configurable via `.env`).

### Available Endpoints

```javascript
// Get top 3 recommendations
bettingAPI.getTop3Bets()

// Get upcoming events
bettingAPI.getUpcomingEvents(sport, limit)

// Get wallet balance
cryptoAPI.getBalance(tokenSymbol)

// Get betting statistics
bettingAPI.getBettingStats()
```

## 🎨 Styling

### Tailwind Configuration

Custom color palette:
- **Primary**: Blue shades for main actions
- **Success**: Green for positive metrics
- **Warning**: Yellow for caution
- **Danger**: Red for high risk

### Custom Components

Pre-built utility classes:
- `.card` - Card container
- `.btn` - Button base
- `.btn-primary` - Primary button
- `.badge` - Badge/tag
- `.stat-card` - Statistics card

## 🔄 Auto-Refresh

The app automatically refreshes data every 60 seconds when enabled:
- Toggle auto-refresh in the header
- Manual refresh button available
- Last update timestamp displayed

## 📊 Features Breakdown

### 1. Top 3 Recommendations
- AI-analyzed betting opportunities
- Ranked by composite score
- Detailed metrics and rationale
- One-click bet placement

### 2. Performance Dashboard
- Total bets placed
- Win rate percentage
- Won/lost/pending counts
- Real-time statistics

### 3. Wallet Integration
- USDT balance display
- Real-time updates
- Multi-currency support (ready)

### 4. Responsive Design
- Mobile-friendly layout
- Tablet optimization
- Desktop experience

## 🚧 Future Enhancements

- [ ] Bet placement modal
- [ ] Historical performance charts
- [ ] Live odds comparison
- [ ] Arbitrage opportunities view
- [ ] User authentication
- [ ] Betting history timeline
- [ ] Custom filters and sorting
- [ ] Dark mode
- [ ] Push notifications
- [ ] Multi-language support

## 🐛 Troubleshooting

### API Connection Issues

```bash
# Check if backend is running
curl http://localhost:8000/health

# Verify CORS settings in backend
# Check config/config.yaml
```

### Build Errors

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

### Styling Issues

```bash
# Rebuild Tailwind
npm run build

# Check PostCSS configuration
cat postcss.config.js
```

## 📝 Development Tips

### Hot Reload

Vite provides instant hot module replacement (HMR):
- Save any file to see changes immediately
- No full page reload needed
- State preservation during updates

### Component Development

```jsx
// Import required dependencies
import React, { useState, useEffect } from 'react';
import { Icon } from 'lucide-react';

// Use Tailwind classes
<div className="card">
  <button className="btn btn-primary">
    Click Me
  </button>
</div>
```

### API Calls

```javascript
// Use the API service
import { bettingAPI } from './services/api';

const fetchData = async () => {
  try {
    const data = await bettingAPI.getTop3Bets();
    console.log(data);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

## 🔐 Security Notes

- Never commit `.env` files
- API keys should be backend-only
- Use environment variables for configuration
- Implement proper authentication in production

## 📄 License

MIT License - Part of the AI Betting Analysis System

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## 📞 Support

- Documentation: `/docs`
- Issues: GitHub Issues
- Backend API: http://localhost:8000/docs

---

**Built with ❤️ using React, Vite, and Tailwind CSS**
