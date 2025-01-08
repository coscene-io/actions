FROM ros:noetic-ros-core

RUN apt-get update \
 && apt-get install -y \
    python3-opencv \
    python3-pip \
    unzip \
    wget \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /root/.cache/pip/*

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

WORKDIR /action
COPY . /action
VOLUME ["/cos/files", "/cos/outputs"]

ENV TOPIC="/video/h264" \
    INPUT_PATHS="/cos/files" \
    OUTPUT_DIR="/cos/outputs"

CMD ["python3", "mp4_to_mcap.py"]
