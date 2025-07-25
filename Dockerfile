FROM python:3.12.4-slim

ARG SECRET_KEY
ARG DEBUG
ARG EMAIL_HOST_USER
ARG GMAIL_APP_PASSWORD

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV SECRET_KEY=$SECRET_KEY
ENV DEBUG=$DEBUG
ENV EMAIL_HOST_USER=$EMAIL_HOST_USER
ENV GMAIL_APP_PASSWORD=$GMAIL_APP_PASSWORD

WORKDIR /daily_task
RUN addgroup --system app && adduser --system --group app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

USER app

EXPOSE 8000

CMD python manage.py migrate && gunicorn --bind 0.0.0.0:$PORT app.wsgi:application