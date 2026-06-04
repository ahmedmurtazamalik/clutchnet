# ClutchNet 
### **Real-Time NBA Win Probability & Game State Engine**

## 1. Executive Summary
**ClutchNet** is an end-to-end machine learning and data streaming platform that calculates and visualizes live NBA win probabilities. By processing historical play-by-play data, a PyTorch-based neural network learns the complex dynamics of basketball games (momentum, time pressure, score differentials). The system then connects to live NBA game feeds, performing sub-second model inferences and pushing results via WebSockets to a high-performance Next.js dashboard. 

This project demonstrates full-stack MLOps, bridging deep learning with event-driven, real-time web architecture.

## 2. Technical Stack
* **Machine Learning & Data Processing:** Python, PyTorch, Pandas, Scikit-Learn, `nba_api`
* **Backend Inference Server:** FastAPI, Uvicorn, Python WebSockets, AsyncIO
* **Frontend Web Application:** Next.js (React), TypeScript, TailwindCSS
* **Data Visualization:** Recharts or D3.js (for high-performance, dynamic SVGs/Canvas)

## 3. System Architecture
The system is divided into two distinct pipelines: The **Training Pipeline** (Offline) and the **Inference Engine** (Online).

### A. Training Pipeline (Offline MLOps)
1. **Data Ingestion:** Scrape the last 5-10 seasons of play-by-play data and box scores using `nba_api`.
2. **Feature Engineering:** Convert raw play logs into a structured time-series dataset. 
3. **Model Training:** Train a Feed-Forward Neural Network (or LSTM for sequence-based context) in PyTorch to output a binary classification probability (Home Team Win = 1, Away Team Win = 0).
4. **Model Serialization:** Export the optimized model weights (`.pt` or ONNX format) for low-latency serving.

### B. Live Inference & Streaming Engine (Online)
1. **Live Poller:** A FastAPI background task continuously polls the NBA live game endpoint (e.g., every 5 seconds).
2. **State Construction:** The backend parses the live JSON feed and constructs a feature vector identical to the training data format.
3. **Inference:** The vector is passed to the loaded PyTorch model in memory, returning the live win probability (e.g., `0.742`).
4. **WebSocket Broadcast:** The updated game state, play description, and probability are pushed via WebSockets to all connected web clients.
5. **Client Rendering:** The Next.js dashboard intercepts the WebSocket event and smoothly animates the UI updates without page reloads.

## 4. Feature Engineering (The ML Inputs)
To accurately predict win probability, the PyTorch model will rely on the following snapshot features at any given moment in the game:
* **Temporal:** `seconds_remaining_in_game`, `quarter`
* **Score Dynamics:** `home_score`, `away_score`, `score_differential`
* **Possession:** `has_possession` (Binary: 1 for Home, 0 for Away), `shot_clock_seconds`
* **Game Context:** `home_team_fouls`, `away_team_fouls`, `home_timeouts_remaining`, `away_timeouts_remaining`
* **Prior Team Strength (Optional but recommended):** Pre-game Elo rating or season Net Rating for both teams to establish a baseline probability before tip-off.

## 5. UI/UX & "Flashy" Visuals (Frontend Features)
The Next.js frontend will serve as a visually striking command center. Key UI components include:

1. **The Pulse Chart (Live Win Probability Graph):**
   * A dynamic, horizontally scrolling line chart.
   * **Visual Hook:** The area under the curve is filled with a gradient. If the line crosses the 50% threshold, the color seamlessly transitions (e.g., from Boston Celtics Green to LA Lakers Purple). 
2. **The "Clutch Indicator" (Play Impact Ticker):**
   * A scrolling sidebar of the latest plays (e.g., *"L. James makes 28-foot three point jumper"*).
   * Next to each play, a glowing badge shows the **Delta (Δ)** of the play. E.g., a massive block or 3-pointer displays a flashing `+12.4% WP`.
3. **Momentum Bar:**
   * A tug-of-war style progress bar at the top of the screen showing current game momentum based on the last 5 minutes of scoring.

## 6. Project Roadmap & Development Phases

### Phase 1: Data Harvesting & Preprocessing (Week 1)
* [ ] Write python scripts to hit `nba_api` and download historical play-by-play logs.
* [ ] Clean data to handle anomalies (overtime, missing data, API rate limits).
* [ ] Engineer the feature vectors and split into train/val/test datasets.

### Phase 2: PyTorch Model Development (Week 2)
* [ ] Define the neural network architecture.
* [ ] Train the model using Binary Cross Entropy Loss.
* [ ] Evaluate model calibration (e.g., when the model predicts 80% win probability, does that team actually win 80% of the time?).
* [ ] Export model weights for inference.

### Phase 3: FastAPI & WebSocket Backend (Week 3)
* [ ] Set up the FastAPI server and load the PyTorch model into memory.
* [ ] Create the live-polling script to track a live (or simulated/replayed) NBA game.
* [ ] Establish the WebSocket (`/ws/live-game`) endpoint.

### Phase 4: Next.js Frontend Development (Week 4)
* [ ] Initialize Next.js project with Tailwind CSS.
* [ ] Connect to the WebSocket and establish state management (React `useState`/`useEffect`).
* [ ] Implement Recharts/D3 to render the live probability curve.
* [ ] Style the dashboard to look like a modern sports analytics broadcast.

## 7. Portfolio Highlighting Strategy
* **The "Demo" Mode:** Because NBA games don't happen 24/7, build a "Demo Mode" toggle in your backend that replays an iconic historical game (e.g., 2016 Finals Game 7, or a crazy multi-overtime game) as if it were happening live. This ensures recruiters can see the dashboard animating anytime they visit.
* **The Pitch:** Emphasize that this isn't just a static Jupyter notebook. You built a **low-latency ML inference pipeline** capable of streaming real-time predictions to concurrent web clients.