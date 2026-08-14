# Deployment

Container definition for running the Streamlit interface.

| File | Purpose |
|---|---|
| `Dockerfile` | Image build — installs from the pinned `requirements.txt` |
| `docker-compose.yml` | Service definition, ports, volumes, safe defaults |
| `.dockerignore` | Keeps secrets and build artefacts out of the image |

## Running

```bash
cd deploy
docker compose up --build
```

Then open http://localhost:8501

## Notes

**The build context is the project root, not this folder.** The image needs
`src/`, `comparison/` and `.api_cache/`, so `docker-compose.yml` sets
`context: ..` explicitly.

**The container defaults to replay mode with a live-call cap.** The flight and
hotel APIs allow 30 and 50 requests *per month*; a container that restarts in a
loop could otherwise spend a whole month's allowance unattended. Override
deliberately if you actually want live data:

```bash
TRIP_PLANNER_API_MODE=record TRIP_PLANNER_MAX_LIVE_CALLS=5 docker compose up
```

**`.env` is read from the project root** and is never copied into the image.
