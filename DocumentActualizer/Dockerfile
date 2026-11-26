FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "requests>=2.32,<3" "beautifulsoup4>=4.12,<5" "psycopg[binary]>=3.2,<4"
COPY *.py ./
CMD ["python","-u","main.py"]
