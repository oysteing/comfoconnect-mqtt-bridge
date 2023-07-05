FROM python

WORKDIR /usr/src/app

RUN pip install --no-cache-dir git+https://github.com/oysteing/comfoconnect-mqtt-bridge

CMD [ "python", "-m", "comfobridge" ]