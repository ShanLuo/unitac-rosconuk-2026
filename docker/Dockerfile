FROM ros:humble-ros-base-jammy

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1

# ROS 2 and system dependencies used by the validated UniTac pipeline.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    v4l-utils \
    libgl1 \
    libglib2.0-0 \
    python3-pip \
    python3-numpy \
    python3-opencv \
    python3-transforms3d \
    ros-humble-cv-bridge \
    ros-humble-image-transport \
    ros-humble-camera-info-manager \
    ros-humble-sensor-msgs \
    ros-humble-geometry-msgs \
    && rm -rf /var/lib/apt/lists/*

# Common Robot Interface (CRI) provides the MG400 backend used by UniTac.
# Keep it external to the MIT-licensed UniTac source tree and pin the exact
# upstream revision used by this workshop image for reproducibility.
ARG CRI_COMMIT=15301cf4132b0482b5e453e724f821ac93bb50b9
RUN git clone https://github.com/robot-dexterity/common-robot-interface.git /opt/common-robot-interface \
    && cd /opt/common-robot-interface \
    && git checkout "${CRI_COMMIT}" \
    && python3 -m pip install --no-cache-dir -e .

WORKDIR /ros2_ws
COPY src /ros2_ws/src

# Build the five UniTac ROS 2 packages into the image.
RUN . /opt/ros/humble/setup.sh \
    && colcon build --symlink-install

COPY . /ros2_ws

RUN printf '%s\n' \
    'source /opt/ros/humble/setup.bash' \
    'source /ros2_ws/install/setup.bash' \
    >> /root/.bashrc

CMD ["bash"]
