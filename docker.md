# Docker Deployment Cheat Sheet for Scrapers

## Overview

This guide covers the complete Docker workflow for deploying Python scrapers to a GCP VM.

---

# 1. Build Docker Image

Build an image from the Dockerfile in the current directory.

```bash
docker build -t magicbricks-scraper .
```

Why:

* Reads Dockerfile
* Installs dependencies
* Packages code into an image

Check images:

```bash
docker images
```

---

# 2. Login to Docker Hub

```bash
docker login
```

Verify:

```bash
docker info | grep Username
```

Expected:

```text
Username: your_username
```

---

# 3. Tag Image

Docker Hub requires:

```text
username/repository:tag
```

Example:

```bash
docker tag magicbricks-scraper nithin0620/magicbricks-scraper:latest
```

Verify:

```bash
docker images
```

---

# 4. Push Image

Upload image to Docker Hub.

```bash
docker push nithin0620/magicbricks-scraper:latest
```

Success output:

```text
latest: digest: sha256:...
```

---

# 5. Setup Docker on GCP VM

Install Docker:

```bash
curl -fsSL https://get.docker.com | sh
```

Add current user to docker group:

```bash
sudo usermod -aG docker $USER
```

Activate group immediately:

```bash
newgrp docker
```

Verify:

```bash
groups
```

Expected:

```text
docker ...
```

Test Docker:

```bash
docker ps
```

---

# 6. Pull Image on VM

```bash
docker pull nithin0620/magicbricks-scraper:latest
```

Verify:

```bash
docker images
```

---

# 7. Create Environment File

Install nano:

```bash
sudo apt update
sudo apt install nano -y
```

Create env file:

```bash
nano .env
```

Example:

```env
DATABASE_URL=postgresql://...
API_KEY=...
```

Verify:

```bash
cat .env
```

---

# 8. Run Container

```bash
docker run -d \
  --name magicbricks-scraper \
  --restart unless-stopped \
  --env-file .env \
  nithin0620/magicbricks-scraper:latest
```

Options:

| Flag                     | Purpose                    |
| ------------------------ | -------------------------- |
| -d                       | Run in background          |
| --name                   | Assign container name      |
| --restart unless-stopped | Auto restart after reboot  |
| --env-file               | Load environment variables |

---

# 9. Check Running Containers

Running containers:

```bash
docker ps
```

All containers:

```bash
docker ps -a
```

---

# 10. View Logs

Show logs:

```bash
docker logs magicbricks-scraper
```

Live logs:

```bash
docker logs -f magicbricks-scraper
```

Last 100 lines:

```bash
docker logs --tail 100 magicbricks-scraper
```

---

# 11. Enter Container

Open shell:

```bash
docker exec -it magicbricks-scraper bash
```

If bash unavailable:

```bash
docker exec -it magicbricks-scraper sh
```

Run commands inside:

```bash
python pipeline.py
```

---

# 12. Container Management

Stop:

```bash
docker stop magicbricks-scraper
```

Start:

```bash
docker start magicbricks-scraper
```

Restart:

```bash
docker restart magicbricks-scraper
```

Remove:

```bash
docker rm magicbricks-scraper
```

Force remove:

```bash
docker rm -f magicbricks-scraper
```

---

# 13. Debugging

Check state:

```bash
docker inspect magicbricks-scraper --format='{{.State.Status}}'
```

Possible outputs:

```text
running
exited
restarting
```

Resource usage:

```bash
docker stats
```

---

# 14. Update Deployment

## Local Machine

Rebuild:

```bash
docker build -t magicbricks-scraper .
```

Tag:

```bash
docker tag magicbricks-scraper nithin0620/magicbricks-scraper:latest
```

Push:

```bash
docker push nithin0620/magicbricks-scraper:latest
```

---

## GCP VM

Pull latest:

```bash
docker pull nithin0620/magicbricks-scraper:latest
```

Stop old container:

```bash
docker stop magicbricks-scraper
```

Remove old container:

```bash
docker rm magicbricks-scraper
```

Start new container:

```bash
docker run -d \
  --name magicbricks-scraper \
  --restart unless-stopped \
  --env-file .env \
  nithin0620/magicbricks-scraper:latest
```

---

# 15. Versioned Releases (Recommended)

Instead of latest:

```bash
docker tag magicbricks-scraper nithin0620/magicbricks-scraper:v1
docker push nithin0620/magicbricks-scraper:v1
```

Next release:

```bash
docker tag magicbricks-scraper nithin0620/magicbricks-scraper:v2
docker push nithin0620/magicbricks-scraper:v2
```

Deploy specific version:

```bash
docker pull nithin0620/magicbricks-scraper:v2
```

Rollback:

```bash
docker pull nithin0620/magicbricks-scraper:v1
```

---

# 16. Cleanup

Remove unused images:

```bash
docker image prune -a
```

Remove everything unused:

```bash
docker system prune -a
```

Check Docker disk usage:

```bash
docker system df
```

---

# Deployment Workflow

```text
Local Development
       ↓
docker build
       ↓
docker tag
       ↓
docker push
       ↓
GCP VM
       ↓
docker pull
       ↓
docker stop
       ↓
docker rm
       ↓
docker run
       ↓
docker logs -f
```
