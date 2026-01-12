# Stock Planner App (TradeWise) 📈

Use AI to seek smarter returns effectively. **Stock Planner App** is a comprehensive trading assistant that combines real-time market data, advanced technical analysis, interactive charting, and state-of-the-art AI/ML insights to help you manage your portfolio and tackle the Indian stock market (NSE/BSE).

![Project Status](https://img.shields.io/badge/status-active-success)
![License](https://img.shields.io/badge/license-MIT-blue)

## ✨ Features

### 🧠 AI & ML Powered
-   **Universal Market Model**: Built-in XGBoost & Random Forest classifier that learns from market data to predict price direction (Buy/Sell signals) with confidence scores.
-   **TradeWise AI Agent**: An integrated chatbot powered by **Google Gemini 2.5**. Ask questions like *"Analyze RELIANCE.NS for a swing trade"* or *"What is my risk on TATASTEEL?"*.
-   **Live Risk Analysis**: Automatic calculation of position sizing, Capital Protection stops (7% Rule), and volatility-based stops (ATR).

### 📊 Interactive Charting
-   **Professional Charts**: TradingView-style charts using `lightweight-charts`.
-   **Indian Market Optimized**: Time-axis explicitly calibrated for IST (Asia/Kolkata).
-   **Visual Overlays**: Displays Previous Close reference line, Dividend/Split markers, and clear Buy/Sell zones.

### 💼 Portfolio Management
-   **Trade Panel**: Dashboard-style widget to track your positions.
-   **P&L Tracking**: Real-time unrealized profit/loss calculation.
-   **Actionable Insights**: Instant "Reduce/Sell" or "Add/Buy" buttons integrated with the order pad.

## 🛠️ Tech Stack

### Frontend
-   **Framework**: [React](https://reactjs.org/) + [Vite](https://vitejs.dev/)
-   **Authentication**: [Supabase](https://supabase.com/)
-   **Styling**: [Tailwind CSS](https://tailwindcss.com/) (Dark Mode support enabled 🌙)
-   **Icons**: [Lucide React](https://lucide.dev/)
-   **Charts**: `lightweight-charts`, `recharts`

### Backend
-   **API**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
-   **Data Processing**: `pandas`, `numpy`, `yfinance`
-   **Machine Learning**: `scikit-learn`, `xgboost`, `joblib`
-   **AI Integration**: `google-generativeai` (Gemini)

## 🚀 Getting Started

Follow these instructions to set up the project locally.

### Prerequisites
-   Python 3.9+
-   Node.js 16+
-   Git

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/stock-planner-app.git
cd stock-planner-app
```

### 2. Backend Setup
Navigate to the backend directory and set up the Python environment.

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Configuration**:
Create a `.env` file in the `backend/` directory:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

**Run Server**:
```bash
python -m uvicorn main:app --reload
```
The backend API will run at `http://localhost:8000`.

### 3. Frontend Setup
Open a new terminal and navigate to the frontend directory.

```bash
cd frontend
npm install
```

**Configuration**:
Create a `.env` file in the `frontend/` directory with the following variables:
```env
VITE_GEMINI_API_KEY=your_gemini_api_key
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_SUPABASE_URL=your_supabase_url
VITE_API_URL=http://localhost:8000
```

**Run Client**:
```bash
npm run dev
```
The application will be available at `http://localhost:5173`.

## 🤖 Usage Guide

1.  **Search Stock**: Enter a symbol (e.g., `INFY`, `HDFCBANK`). The app defaults to `.NS` (NSE) if no extension is provided.
2.  **Analyze**: View the "Verdict" card for the ML model's prediction and the "Technical" score.
3.  **Chat with AI**: targeted questions. Try: *"Plan a trade for this stock with 1L capital."*
4.  **Track Trade**: Use the "Add/Buy" button to record a paper trade and monitor P&L in the Trade Panel.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
