FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
RUN python -c "import tomllib; p=tomllib.load(open('pyproject.toml','rb'))['project']; print(*p['dependencies'], *p['optional-dependencies']['api'], sep='\n')" > /tmp/requirements && pip install --no-cache-dir -r /tmp/requirements
COPY src src
COPY document_templates document_templates
RUN pip install --no-deps .
CMD ["uvicorn","document_generator.api:app","--host","0.0.0.0","--port","8000"]
