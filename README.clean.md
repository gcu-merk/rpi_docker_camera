# rpi_docker_camera

Small Docker service that captures images from a Raspberry Pi AI Camera (Pi 5) using libcamera and saves them to an external SSD. The service updates Redis with the latest capture timestamp and the absolute host path to the image. It keeps only the most recent images to limit storage.

## Quick summary

- Capture cadence: default 5s (CAPTURE_INTERVAL)
- Retention: keep latest 10 images (MAX_SAVED)
- Container output dir: `/captures` (OUTPUT_DIR)
- Host mount (recommended): `/mnt/storage/camera_capture/rpi_docker_camera`

## Run locally (docker-compose)

1. Mount your external SSD on the Pi at `/mnt/storage/camera_capture/rpi_docker_camera`.
2. Start the stack:

```powershell
docker compose up -d --build
```

The compose file starts Redis and the camera service. The camera container requires privileged access and maps `/dev/vchiq` so libcamera can access the camera.

## Environment variables

The camera container supports configuration via environment variables. Key options:

- OUTPUT_DIR: where the container writes images (default `/captures`)
- HOST_OUTPUT_PATH: host absolute path to the same directory (recommended)
- CAPTURE_CMD: capture command template (default `libcamera-jpeg -o {path} -n`)
- CAPTURE_INTERVAL: seconds between captures (default `5`)
- MAX_SAVED: how many recent images to keep (default `10`)
- REDIS_HOST / REDIS_PORT / REDIS_DB / REDIS_KEY: Redis connection and key (default `camera:latest`)

When `HOST_OUTPUT_PATH` is set, Redis receives the host absolute path for the latest image. This is helpful for other services that consume the image path.

## GitHub Actions (CI/CD)

The workflow `.github/workflows/deploy-to-pi.yml` builds an `arm64` image and pushes to Docker Hub, then SSHes to your Pi to pull and run the image. Required repository secrets:

- DOCKERHUB_USERNAME
- DOCKERHUB_TOKEN
- PI_HOST
- PI_SSH_KEY

The workflow uses `merk` as the deploy user by default. If you need a different username, edit the workflow or set the appropriate environment in the job steps.

## Notes

- The container requires privileged access to the camera device (`/dev/vchiq`).
- Redis entries are written as a hash with `timestamp` and `path` fields; `path` will be the host path when `HOST_OUTPUT_PATH` is provided.
- Adjust `MAX_SAVED` to control retention.

## License

See the `LICENSE` file in this repository.
