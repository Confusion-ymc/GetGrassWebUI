FROM python:3.11.4-slim-bullseye

WORKDIR /getGrassWebUI

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "main.py"]