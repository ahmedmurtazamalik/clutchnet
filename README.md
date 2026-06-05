# ClutchNet: Real-Time NBA Win Probability Engine

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-Deep_Learning-EE4C2C.svg)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-WebSockets-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-React-000000.svg)](https://nextjs.org/)

## Overview
**ClutchNet** is an end-to-end machine learning platform that calculates and visualizes live NBA win probabilities. By bridging deep learning with event-driven web architecture, the system consumes live play-by-play data, performs sub-second inferences using a custom PyTorch neural network, and streams the shifting game dynamics to a high-performance Next.js dashboard via WebSockets.

This project goes beyond static data science notebooks by demonstrating a complete MLOps lifecycle: from historical data ingestion and feature engineering to low-latency model serving and real-time frontend rendering.

## Core Features
* **Live Inference Engine:** Parses live NBA game feeds, constructs feature vectors on the fly, and generates win probabilities in milliseconds.
* **The Pulse Chart:** A dynamic, Recharts-powered interactive dashboard that draws the win probability curve in real-time. The UI features contextual gradients that seamlessly shift colors based on which team is favored.
* **Clutch Impact Ticker:** A live play-by-play feed that calculates and displays the specific Delta (Δ) of every play. (e.g., highlighting exactly how much a step-back 3-pointer shifted the mathematical momentum of the game).
* **Historical Replay (Demo Mode):** A built-in simulation engine that allows users to replay iconic historical games (e.g., 2016 Finals Game 7) at accelerated speeds to observe the model's performance and dashboard animations without waiting for a live game.

## System Architecture

The architecture is divided into two distinct pipelines to separate the heavy computational training from the low-latency streaming environment.

### 1. Offline MLOps Pipeline (Training)
The foundation of the model relies on a robust data ingestion pipeline that interfaces with the `nba_api`. The system scrapes, cleans, and structures over a decade of historical play-by-play logs and box scores. This raw data is transformed into a rich time-series dataset. A Feed-Forward Neural Network (built in PyTorch) is then trained on these millions of micro-game states to accurately map game contexts to final outcomes. The optimized weights are serialized for deployment.

### 2. Online Inference & Streaming Engine
During a game, a FastAPI background worker continuously polls live NBA endpoints. Upon detecting a new play, the backend constructs a snapshot vector matching the training architecture, passes it through the in-memory PyTorch model, and broadcasts the resulting probability via WebSockets. The Next.js client intercepts these asynchronous events, animating the UI updates smoothly without requiring page reloads.

## Machine Learning Approach & Feature Engineering
To accurately capture the complex dynamics of a basketball game, the neural network evaluates a comprehensive snapshot of the game state at any given second. The primary features processed by the model include:

* **Temporal Context:** Time remaining in the quarter, time remaining in the game.
* **Score Dynamics:** Current score differential, home score, away score.
* **Possession Mechanics:** Binary possession indicators and shot clock pressure.
* **Resource Constraints:** Remaining timeouts and team foul penalty states.
* **Baseline Strength:** Pre-game team Elo ratings or season net ratings to anchor the probability prior to tip-off.

## Technology Stack

**Backend & AI**
* **Machine Learning:** Python, PyTorch, Pandas, Scikit-Learn
* **Data Sourcing:** `nba_api`
* **Server:** FastAPI, Uvicorn, Python AsyncIO, WebSockets

**Frontend**
* **Framework:** Next.js (React), TypeScript
* **Styling:** TailwindCSS
* **Visualization:** Recharts / D3.js

## Running the Project Locally

### Prerequisites
* Python 3.10+
* Node.js 18+

### Setup Instructions
1. **Clone the repository:**
   `git clone https://github.com/yourusername/ClutchNet.git`
2. **Setup the Python Backend:**
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
3. **Setup the Next.js Frontend:**
   cd frontend
   npm install
   npm run dev
4. **Access the Application:** Open `http://localhost:3000` in your browser. Use the UI toggle to activate "Demo Mode" to see the live data stream in action.