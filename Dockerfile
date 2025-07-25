FROM python:3.12-slim

WORKDIR /daily_task

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y git

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD python manage.py migrate && gunicorn --bind 0.0.0.0:$PORT app.wsgi:application