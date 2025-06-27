
FROM python:3.11-slim-buster

COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt
ENV PYTHONUNBUFFERED=TRUE

ENTRYPOINT ["python3"]