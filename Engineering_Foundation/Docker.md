# Docker

- Docker is a tool that packages your application and everything it needs to run (code, libraries, system tools, settings) into a lightweight, portable unit called a container, so it runs the same way on any machine.

# Sub-concepts

- **The problem Docker solves.** Different computers (your laptop, a colleague’s laptop, a cloud server) often have different operating system versions, library versions, and configurations. This creates the classic “works on my machine” nightmare. Docker eliminates that by bundling the app with its exact environment.

- **Images vs Containers.**
    - An image is a read-only template (like a blueprint or a class in programming). It contains the application code, runtime, libraries, and settings.
    - A container is a running instance of an image (like an object created from a class). You can start, stop, and delete containers; the image stays unchanged.

- **Dockerfile.** 
    - A simple text file with step-by-step instructions that tell Docker how to build an image. Each instruction creates a new layer.

- **Basic workflow.**
    - Write a Dockerfile.
    - Build an image from it.
    - Run one or more containers from that image.
    - Share **the image** (via Docker Hub or a private registry) so others can run the exact same thing.

- Key benefits for AI/ML work. Reproducible environments, easy dependency management (Python packages, CUDA, system libraries), consistent training and serving setups, and simple deployment to any cloud or server.

## Docker file example

```dockerfile
# Dockerfile
FROM python:3.11-slim                                                   # start from an official lightweight Python image

WORKDIR /app                                                            # set the working directory inside the container

COPY requirements.txt .                                                 # copy dependency list
RUN pip install --no-cache-dir -r requirements.txt

COPY . .                                                                # copy the rest of the application code

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Commands

```bash
# Build the image
docker build -t my-fastapi-app .

# Run a container from the image
docker run -p 8000:8000 my-fastapi-app

# Useful everyday commands
docker images                  # list images
docker ps                      # list running containers
docker stop <container_id>     # stop a container
docker rm <container_id>       # delete a container
docker rmi my-fastapi-app      # delete an image
```

## Comparison / alternatives

- Virtual machines (VMs): Also isolate environments, but they package a whole operating system and are much heavier and slower to start. Containers share the host OS kernel and start in seconds.
- conda / virtualenv / poetry: Great for Python package isolation, but they do not package system-level dependencies (CUDA drivers, system libraries, etc.) and do not solve the “different OS” problem.
- Kubernetes: Orchestrates many containers across machines; Docker is what creates and runs the individual containers that Kubernetes manages.

## Mind map

```text
Docker
├── Problem it solves (“works on my machine”)
├── Image (blueprint) vs Container (running instance)
├── Dockerfile (instructions to build an image)
├── Basic commands (build, run, ps, stop, rm)
├── Benefits for AI/ML (reproducibility, dependencies)
└── vs VMs / virtualenv / Kubernetes
```