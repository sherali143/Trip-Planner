FROM python:3.11-slim

WORKDIR /app

# requirements.txt is the pinned source of truth — it holds the exact versions
# the published evaluation results were produced with. (This previously used
# poetry + poetry.lock, which had drifted out of sync with those pins.)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# The Streamlit app is src/ui/app.py. This previously pointed at "app.py" in
# the project root, which does not exist — the container started and died.
CMD ["streamlit", "run", "src/ui/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0"]
