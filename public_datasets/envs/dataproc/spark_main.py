"""Dataproc entry point: the job itself is public_datasets.pipeline.spark_job (installed in the image)."""
import sys

from public_datasets.pipeline.spark_job import main

if __name__ == '__main__':
    sys.exit(main())
