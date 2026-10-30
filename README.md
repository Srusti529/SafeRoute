# SafeRoute: AI-Based Safety-Aware Navigation System for Women

Suggests routes that balance **safety, time and distance** using crime-hotspot analysis
(K-Means) and a Random Forest risk model, on OpenStreetMap data.

## Quick start
```bash
git clone https://github.com/<owner>/<repo>.git
cd <repo>
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m ml.generate_sample_data   # fake data for development ONLY
python -m ml.train                  # trains models, prints accuracy
python -m backend.app               # open http://127.0.0.1:5000
python -m unittest discover -s tests -v
```
Needs internet when running (OSRM routes, OpenStreetMap map tiles and place search).

## Project layout
| Folder | Purpose |
|---|---|
| `data/raw` | crime CSV: columns `lat, lon, hour, severity` (+ optional extras) |
| `ml/` | data generation, training, risk prediction |
| `backend/` | Flask API: routing, scoring, facilities, incident reports |
| `frontend/` | map page (Leaflet), CSS, JS |
| `tests/` | unit tests |
| `docs/` | issues list, report, diagrams |

## Team workflow
1. `git checkout dev && git pull`
2. `git checkout -b feature/<short-name>`
3. Commit small and often: `git commit -m "Add hotspot labels"`
4. `git push -u origin feature/<short-name>` then open a Pull Request into `dev`
5. A teammate reviews and merges. Only `dev` merges into `main`.

## Limitations
- The sample dataset is synthetic. Replace `data/raw/crime.csv` with real data.
- The free OSRM demo server uses driving routes and returns few alternatives.
- Risk is an estimate from past data, not a guarantee of safety.
