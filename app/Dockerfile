FROM python:3.9

RUN mkdir /app
COPY app/app.py /app

WORKDIR /app

COPY requirements.txt  .
RUN pip install -r requirements.txt

ENTRYPOINT ["python"]

CMD ["app.py"]
