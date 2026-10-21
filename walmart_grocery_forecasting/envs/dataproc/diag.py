"""Diagnostic batch: what Spark does this workload get, and where do its tasks run? Prints one JSON line (DIAG ...).

Uses only the standard library and pyspark, so it runs with or without our custom container.
"""
import json
import os
import socket
import sys
import time

from pyspark.sql import SparkSession


def where(i):
    t0 = time.time()
    x = sum(k * k for k in range(200_000))  # a little work, so tasks overlap
    return i, socket.gethostname(), os.getpid(), t0, time.time(), x > 0


def main():
    t_start = time.time()
    spark = SparkSession.builder.appName('diag').getOrCreate()
    sc = spark.sparkContext
    t_session = time.time()
    tracker = sc._jsc.sc().statusTracker()
    seen = []
    for _ in range(0 if sc.master.startswith('local') else 36):  # up to 3 minutes for executors
        seen.append(len(tracker.getExecutorInfos()) - 1)
        if seen[-1] >= int(sc.getConf().get('spark.executor.instances', '0') or 0) > 0:
            break
        time.sleep(5)
    t_exec = time.time()
    rows = sc.parallelize(range(64), 16).map(where).collect()
    t_done = time.time()
    hosts = {}
    for _, h, pid, a, b, _ in rows:
        hosts.setdefault(h, set()).add(pid)
    conf = {k: v for k, v in sc.getConf().getAll()
            if k.startswith(('spark.master', 'spark.executor', 'spark.driver', 'spark.dynamic', 'spark.submit',
                             'spark.kubernetes', 'spark.dataproc', 'spark.default'))}
    import pyspark
    print('DIAG ' + json.dumps({
        'master': sc.master, 'defaultParallelism': sc.defaultParallelism,
        'executors_seen_over_time': seen, 'executor_ids': [e.host() + ':' + str(e.port()) for e in tracker.getExecutorInfos()],
        'task_hosts': {h: len(p) for h, p in hosts.items()}, 'driver_host': socket.gethostname(),
        'python': sys.executable, 'pyspark': pyspark.__file__, 'pyspark_version': pyspark.__version__,
        'env': {k: v for k, v in os.environ.items() if k.startswith(('SPARK', 'PYSPARK', 'JAVA_HOME'))},
        'conf': conf, 'seconds': {'session': t_session - t_start, 'executor_wait': t_exec - t_session,
                                  'tasks': t_done - t_exec},
    }, sort_keys=True), flush=True)
    spark.stop()


if __name__ == '__main__':
    main()
