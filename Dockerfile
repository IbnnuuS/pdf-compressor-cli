FROM python:3.10-slim

# Install system dependencies including Ghostscript
RUN apt-get update && apt-get install -y \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Set up user permissions for Hugging Face (runs as user with UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy requirements and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application files
COPY --chown=user . .

# Create upload and output directories
RUN mkdir -p uploads output

# Hugging Face runs on port 7860 by default
EXPOSE 7860

CMD ["python", "app.py"]