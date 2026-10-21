# Docker (local Linux image)

The same pipeline as [local](../local/), in a Linux container: `python:3.12-slim`, runtime dependencies pinned from
the repo's `uv.lock`, prophet-batch installed from a wheel built from the clone next to this repo.

```sh
sh walmart_grocery_forecasting/envs/docker/build.sh          # image prophet-batch-examples/walmart:local
sh walmart_grocery_forecasting/envs/docker/run.sh            # all three model variants, all 1,437 items
sh walmart_grocery_forecasting/envs/docker/run.sh --n 50     # quick check; arguments go to pipeline.run
```

`run.sh` mounts the repo's `data/` (the container downloads and verifies the M5 archive into it if missing) and
`results/runs/` (outputs: `docker-<model>-<n>-<timestamp>.{json,npz,md}`). To run the image by hand:

```sh
docker run --rm -v "$PWD/data:/app/data" \
  -v "$PWD/walmart_grocery_forecasting/results/runs:/app/walmart_grocery_forecasting/results/runs" \
  prophet-batch-examples/walmart:local --model events_snap --workers 4
```

Each result records the container's CPU count and the prophet-batch and examples commits baked in at build time.
Docker Desktop on a Mac runs a Linux VM: give it all cores (Settings → Resources) to compare with the native run.
For an x86-64 image (e.g. for Cloud Run), pass `--platform linux/amd64` to `build.sh`; on Apple Silicon it runs
under emulation, so don't time it there.
