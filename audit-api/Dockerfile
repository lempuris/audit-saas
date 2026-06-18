FROM python:3.12-slim

# WeasyPrint (PDF rendering) needs Pango + Fontconfig + HarfBuzz at runtime,
# plus a base font. Installed here so the image can render report PDFs.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libfontconfig1 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8.13 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# The exec bit can be lost when the image is built from a Windows checkout.
RUN chmod +x entrypoint.sh

EXPOSE 5000

CMD ["./entrypoint.sh"]
