FROM ros:humble-ros-base-jammy
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip python3-dev git v4l-utils libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY requirements.txt pyproject.toml ./
COPY src ./src
RUN python3 -m pip install --upgrade pip && python3 -m pip install -e .
COPY . /workspace
ENV PYTHONPATH=/workspace/src
CMD ["bash"]
