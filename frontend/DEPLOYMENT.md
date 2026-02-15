# Deployment Guide - AI Betting Analysis Frontend

Complete guide for deploying the React frontend to various platforms.

## 📋 Prerequisites

- Node.js 18+ installed
- npm or yarn package manager
- Backend API running and accessible
- Environment variables configured

## 🚀 Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Build Docker Image

```bash
# Build the image
docker build -t betting-ai-frontend:latest .

# Run the container
docker run -d \
  -p 80:80 \
  -e VITE_API_URL=http://your-backend-url:8000 \
  --name betting-frontend \
  betting-ai-frontend:latest
```

#### Using Docker Compose

```bash
# Deploy with docker-compose
docker-compose -f docker-compose.deploy.yml up -d

# View logs
docker-compose -f docker-compose.deploy.yml logs -f frontend

# Stop services
docker-compose -f docker-compose.deploy.yml down
```

**Access:** http://localhost

---

### Option 2: Vercel Deployment

#### Quick Deploy

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

#### Configuration

1. Create project on [Vercel Dashboard](https://vercel.com)
2. Connect your Git repository
3. Set environment variables:
   - `VITE_API_URL`: Your backend API URL
   - `VITE_ENV`: production
4. Deploy automatically on push

**Features:**
- ✅ Automatic HTTPS
- ✅ Global CDN
- ✅ Automatic deployments
- ✅ Preview deployments for PRs

---

### Option 3: Netlify Deployment

#### Quick Deploy

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login to Netlify
netlify login

# Deploy
netlify deploy --prod
```

#### Configuration

1. Create site on [Netlify Dashboard](https://netlify.com)
2. Connect your Git repository
3. Build settings:
   - Build command: `npm run build`
   - Publish directory: `dist`
4. Environment variables:
   - `VITE_API_URL`: Your backend API URL
   - `VITE_ENV`: production

**Features:**
- ✅ Automatic HTTPS
- ✅ Global CDN
- ✅ Form handling
- ✅ Serverless functions

---

### Option 4: AWS S3 + CloudFront

#### Build and Upload

```bash
# Build the application
npm run build

# Install AWS CLI
# brew install awscli  # macOS
# apt-get install awscli  # Ubuntu

# Configure AWS credentials
aws configure

# Create S3 bucket
aws s3 mb s3://betting-ai-frontend

# Enable static website hosting
aws s3 website s3://betting-ai-frontend \
  --index-document index.html \
  --error-document index.html

# Upload files
aws s3 sync dist/ s3://betting-ai-frontend --delete

# Set public read permissions
aws s3api put-bucket-policy \
  --bucket betting-ai-frontend \
  --policy file://s3-policy.json
```

#### S3 Policy (s3-policy.json)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::betting-ai-frontend/*"
    }
  ]
}
```

#### CloudFront Setup

1. Create CloudFront distribution
2. Origin: S3 bucket
3. Default root object: `index.html`
4. Error pages: 404 → /index.html (for SPA routing)
5. Enable HTTPS

---

### Option 5: DigitalOcean App Platform

#### Deploy via CLI

```bash
# Install doctl
# brew install doctl  # macOS

# Authenticate
doctl auth init

# Create app
doctl apps create --spec .do/app.yaml
```

#### App Spec (.do/app.yaml)

```yaml
name: betting-ai-frontend
services:
  - name: web
    github:
      repo: your-username/betting-ai-system
      branch: main
      deploy_on_push: true
    build_command: npm run build
    run_command: npm run preview
    envs:
      - key: VITE_API_URL
        value: https://your-backend-url.com
      - key: VITE_ENV
        value: production
    http_port: 4173
    routes:
      - path: /
```

---

### Option 6: Traditional VPS (Ubuntu/Nginx)

#### Server Setup

```bash
# SSH into your server
ssh user@your-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Nginx
sudo apt install -y nginx

# Install PM2 (process manager)
sudo npm install -g pm2
```

#### Deploy Application

```bash
# Clone repository
git clone https://github.com/your-username/betting-ai-system.git
cd betting-ai-system/frontend

# Install dependencies
npm install

# Build application
npm run build

# Copy build to web root
sudo cp -r dist/* /var/www/html/

# Or serve with a simple HTTP server
npm install -g serve
pm2 start "serve -s dist -l 3000" --name betting-frontend
pm2 save
pm2 startup
```

#### Nginx Configuration

```bash
# Create Nginx config
sudo nano /etc/nginx/sites-available/betting-ai
```

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/betting-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo certbot renew --dry-run
```

---

### Option 7: GitHub Pages

#### Deploy Script

```bash
# Install gh-pages
npm install -g gh-pages

# Add to package.json scripts
"deploy": "npm run build && gh-pages -d dist"

# Deploy
npm run deploy
```

#### Configuration

1. Enable GitHub Pages in repository settings
2. Source: gh-pages branch
3. Custom domain (optional)

**Note:** GitHub Pages doesn't support server-side routing well. Consider using hash routing or a different platform.

---

## 🔧 Build Configuration

### Production Build

```bash
# Standard build
npm run build

# Build with custom API URL
VITE_API_URL=https://api.production.com npm run build

# Preview production build locally
npm run preview
```

### Build Output

```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   ├── index-[hash].css
│   └── [other assets]
└── [other files]
```

---

## 🌍 Environment Variables

### Development (.env)
```env
VITE_API_URL=http://localhost:8000
VITE_ENV=development
```

### Production (.env.production)
```env
VITE_API_URL=https://api.yourdomain.com
VITE_ENV=production
```

### Setting Variables by Platform

**Vercel:**
```bash
vercel env add VITE_API_URL production
```

**Netlify:**
```bash
netlify env:set VITE_API_URL https://api.yourdomain.com
```

**Docker:**
```bash
docker run -e VITE_API_URL=https://api.yourdomain.com ...
```

---

## 🔒 Security Checklist

- [ ] Enable HTTPS (SSL/TLS)
- [ ] Set security headers (CSP, X-Frame-Options, etc.)
- [ ] Configure CORS on backend
- [ ] Use environment variables for sensitive data
- [ ] Enable rate limiting
- [ ] Set up monitoring and logging
- [ ] Regular security updates
- [ ] Implement authentication if needed

---

## 📊 Performance Optimization

### Build Optimizations

```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          charts: ['recharts'],
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
}
```

### CDN Configuration

- Use CDN for static assets
- Enable Gzip/Brotli compression
- Set proper cache headers
- Implement lazy loading

---

## 🐛 Troubleshooting

### Build Fails

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run build
```

### API Connection Issues

1. Check CORS settings on backend
2. Verify API URL in environment variables
3. Check network/firewall rules
4. Test API endpoint directly

### Blank Page After Deploy

1. Check browser console for errors
2. Verify base URL in vite.config.js
3. Check routing configuration
4. Ensure all assets are uploaded

### 404 on Refresh

Configure server to serve index.html for all routes:
- Nginx: `try_files $uri $uri/ /index.html;`
- Apache: Use .htaccess with RewriteRule
- Vercel/Netlify: Automatic with config files

---

## 📈 Monitoring

### Setup Monitoring

```bash
# Install Sentry
npm install @sentry/react

# Configure in main.jsx
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "your-sentry-dsn",
  environment: import.meta.env.VITE_ENV,
});
```

### Analytics

```bash
# Google Analytics
npm install react-ga4

# Configure
import ReactGA from 'react-ga4';
ReactGA.initialize('G-XXXXXXXXXX');
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions (.github/workflows/deploy.yml)

```yaml
name: Deploy Frontend

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
        working-directory: ./frontend
      
      - name: Build
        run: npm run build
        working-directory: ./frontend
        env:
          VITE_API_URL: ${{ secrets.VITE_API_URL }}
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
          working-directory: ./frontend
```

---

## 📝 Deployment Checklist

Before deploying to production:

- [ ] Update environment variables
- [ ] Test build locally (`npm run build && npm run preview`)
- [ ] Check all API endpoints work
- [ ] Verify CORS configuration
- [ ] Test on multiple browsers
- [ ] Test responsive design
- [ ] Enable HTTPS
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Document deployment process
- [ ] Set up CI/CD pipeline
- [ ] Test error handling
- [ ] Verify analytics tracking

---

## 🎯 Recommended Setup

**For Production:**
1. **Frontend:** Vercel or Netlify (easiest, automatic HTTPS, CDN)
2. **Backend:** DigitalOcean App Platform or AWS ECS
3. **Database:** Managed PostgreSQL (AWS RDS, DigitalOcean)
4. **Monitoring:** Sentry for errors, Google Analytics for usage

**For Development:**
1. **Frontend:** Local dev server (`npm run dev`)
2. **Backend:** Docker Compose
3. **Database:** Local PostgreSQL in Docker

---

## 📞 Support

- Documentation: `/docs`
- Issues: GitHub Issues
- Backend API: Check backend deployment guide

---

**Choose the deployment option that best fits your needs and infrastructure! 🚀**
