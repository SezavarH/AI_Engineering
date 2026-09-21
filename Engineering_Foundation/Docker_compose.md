# Docker Compose

- Docker Compose is a tool that lets you **define and run multi-container applications with a single simple configuration file**, so you can start your entire stack (app + database + cache + etc.) with one command instead of starting each container by hand.

## Analogy

- If a single Docker container is one musician, 
- Docker Compose is the conductor with a score (the YAML file). 
- The conductor tells every musician exactly what instrument to play, how to connect to the others, and when to start — so the whole orchestra plays together with one wave of the baton (**docker compose up**).

## Sub-concepts

- **The problem it solves.** Real applications almost never run as a single container. You usually need your FastAPI app + a PostgreSQL database + Redis + maybe a worker. Starting and linking them all with long docker run commands is painful and error-prone.

- **The Compose file.** A YAML file (almost always named docker-compose.yml or compose.yaml) that describes:
    - Which services (containers) you need
    - Which images or Dockerfiles to use
    - Ports,  environment variables, volumes, networks, and dependencies between services

- **Services.** Each container in your application is declared as a “service.” Compose gives them nice names (e.g. web, db) and automatically puts them on the same network so they can talk to each other by name.

- **One-command lifecycle.**
    - docker compose up → build (if needed) and start everything
    - docker compose down → stop and clean up
    - docker compose logs → see logs from all services
    - docker compose ps → see status of everything

- **Common extras.** Volumes (so database data survives container restarts), environment variables, depends_on (start order), and profiles (run only certain services).

## docker-compose file

```YAML
# docker-compose.yml
services:
  web:                              # your FastAPI app
    build: .                        # build from the Dockerfile in current folder
    ports:
      - "8000:8000"                 # host:container
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      - db                          # wait for db to start first

  db:                               # PostgreSQL database
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data   # keep data between restarts

volumes:
  postgres_data:                    # named volume declaration

```

## commands

```bash
# Start the whole stack
docker compose up --build

# Run in the background
docker compose up -d

# Stop and remove containers (data in volumes is kept)
docker compose down

# View logs
docker compose logs -f web
```

## Mind map

```text
Docker Compose
├── Problem it solves (multi-container apps)
├── compose.yaml / docker-compose.yml
├── Services (named containers)
├── Key features
│   ├── Networking (talk by service name)
│   ├── Volumes (persistent data)
│   ├── Environment variables
│   └── depends_on (startup order)
├── Main commands (up, down, logs, ps)
└── vs plain docker run / Kubernetes
```