FROM python:3.12-slim

WORKDIR /app

COPY engine/pyproject.toml .
RUN pip install --no-cache-dir .

COPY engine/malu/ malu/

EXPOSE 8000

CMD ["uvicorn", "malu.main:app", "--host", "0.0.0.0", "--port", "8000"]
