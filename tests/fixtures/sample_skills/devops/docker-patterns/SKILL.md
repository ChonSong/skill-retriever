---
name: docker-patterns
description: Docker and Docker Compose patterns for local development, container orchestration, and deployment workflows.
version: 1.0.0
metadata:
  hermes:
    tags: [docker, devops, deployment]
    category: devops
---

# Docker Patterns

## When to Use
- Setting up local development environments
- Configuring Docker Compose for multi-service apps
- Debugging container networking issues

## Procedure
1. Write your `Dockerfile` with multi-stage builds
2. Define services in `docker-compose.yml`
3. Run `docker compose up -d`

## Pitfalls
- Volume mounts can cause permission issues
- Container names must be unique
