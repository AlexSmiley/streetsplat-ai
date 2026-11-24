# StreetSplat AI
MVP: Google Maps location metadata + authorized perspective photos or MP4 -> Nerfstudio COLMAP processing -> Splatfacto training -> Gaussian PLY -> browser viewer. No Google imagery is fetched. Coordinates are metadata only, not georeferencing. Panorama projection, automatic imagery acquisition and SPLAT conversion are not implemented.

Install Nerfstudio with CUDA, COLMAP and FFmpeg following https://docs.nerf.studio/quickstart/installation.html in a dedicated GPU environment. Ensure ns-process-data, ns-train and ns-export are on PATH.

```sh
cd backend
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```
In another terminal:
```sh
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. Upload overlapping perspective photographs or an MP4 of the selected street. Three photos is only the minimum accepted input; use many overlapping views. The default URL selects the requested location. Jobs are serialized and stored in memory; restart loses status. This is a trusted local single-user prototype, not an authenticated public API. Do not expose it publicly without authentication, quotas, persistent queue and HTTPS. Vercel can build the frontend from frontend/; set VITE_API_URL to a secured HTTPS worker gateway and ORIGINS to the frontend origin. No public gateway is provided.

Tests: `cd backend && pytest -q`. GPU training and browser integration require external dependencies and real imagery.
