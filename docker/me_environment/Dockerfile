FROM nvidia/cuda:12.1.1-devel-ubuntu22.04
LABEL description="ME project environment (docs: https://github.com/vincenzo-scotti/xai_me)."
# Install required tools
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y git build-essential \
    python3 python3-pip default-jdk default-jre \
    wget
RUN python3 -m pip install --no-cache-dir --upgrade pip
# Create working directory
RUN mkdir /app
RUN mkdir /app/xai_me
# Declare volumes
VOLUME /app/me_project/resources
VOLUME /app/me_project/experiments
VOLUME /app/me_project/notebooks
VOLUME /app/me_project/services
VOLUME /app/me_project/src
VOLUME /app/me_project/submodules
# Set current working directory
WORKDIR /app/me_project
# Copy requirement files
COPY submodules/llm_cstk/requirements.txt .llm_cstk_requirements.txt
COPY requirements.txt .me_requirements.txt
# Install required packages
RUN --mount=type=cache,target=/root/.cache/pip python3 -m pip install -r .llm_cstk_requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip python3 -m pip install -r .me_requirements.txt
# Update Python path
ENV PYTHONPATH "${PYTHONPATH}:/app/me_project/src"
ENV PYTHONPATH "${PYTHONPATH}:/app/me_project/src/web_app"
ENV PYTHONPATH "${PYTHONPATH}:/app/me_project/submodules/llm_cstk/src"
# Update timezone
ENV TZ UTC
# Set host to allow external access
ENV HOST 0.0.0.0
# Port mappig
EXPOSE 8000
EXPOSE 8888