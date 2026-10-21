# Local stand-in for Dataproc Serverless: the job image plus what Dataproc mounts at runtime (a JRE and Spark, here
# pyspark from pip). Defaults match runtime 2.3 (Spark 3.5.3, Java 17). Build the base natively first:
#   PLATFORM=linux/arm64 TAG=prophet-batch-examples/walmart-spark:native sh ../build.sh
ARG BASE=prophet-batch-examples/walmart-spark:native
ARG JAVA=17
FROM eclipse-temurin:${JAVA}-jre AS jre
FROM ${BASE}
ARG PYSPARK=3.5.3
USER root
COPY --from=jre /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk PATH=/opt/java/openjdk/bin:$PATH
RUN pip install --no-cache-dir pyspark==${PYSPARK}
USER spark
