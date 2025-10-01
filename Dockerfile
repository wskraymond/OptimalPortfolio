#  # Use the official VS Code devcontainers base image
# FROM mcr.microsoft.com/vscode/devcontainers/base:debian

# Use the official slim Python image
FROM python:3-slim

# Update package list and install necessary tools
RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    build-essential \
    sudo \
    git \
    curl

# Install Docker CLI
RUN apt-get install -y --no-install-recommends docker.io

# Clean up to reduce image size
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

# Set up a non-root user with sudo access (optional)
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME
RUN useradd --uid $USER_UID --gid $USER_GID -m $USERNAME
RUN echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME
RUN chmod 0440 /etc/sudoers.d/$USERNAME
RUN usermod -aG docker $USERNAME

# Switch to the non-root user
USER $USERNAME

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/home/$USERNAME/.local/bin:$PATH"

# Set the default shell to bash rather than sh
ENV SHELL /bin/bash

# # Copy the project files into the container
# COPY pydsa /workspace/pydsa

# # Set the working directory
# WORKDIR /workspace/pydsa

# Default command
CMD ["bash"]





