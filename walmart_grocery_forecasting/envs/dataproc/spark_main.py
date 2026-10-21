"""Dataproc entry point: the job itself is walmart_grocery_forecasting.pipeline.spark_job (installed in the image)."""
import sys

from walmart_grocery_forecasting.pipeline.spark_job import main

if __name__ == '__main__':
    sys.exit(main())
