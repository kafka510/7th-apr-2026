# Dockerfile
FROM python:3.11
 
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
 
WORKDIR /code
 
# Install system dependencies required for Playwright Chromium
# These are essential for Chromium to run in headless mode
# Updated package names for Debian Trixie
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libgtk-3-0 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
&& rm -rf /var/lib/apt/lists/*
 
COPY requirements.txt /code/
RUN pip install --upgrade pip && pip install -r requirements.txt
 
# Install all Playwright browsers (Chromium, Firefox, WebKit)
# This installs all browsers needed for dashboard screenshots
RUN playwright install
 
COPY . /code/
 
# Collect static files (optional, if you use Django staticfiles)
RUN python manage.py collectstatic --noinput
 
#CMD ["gunicorn", "web_app.wsgi:application", "--bind", "0.0.0.0:8000"]