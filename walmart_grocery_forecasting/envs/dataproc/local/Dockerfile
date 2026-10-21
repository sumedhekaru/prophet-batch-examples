# Local stand-in for Dataproc Serverless: the job image plus what Dataproc mounts at runtime (a Java 21 JRE and Spark
# 4.0, here pyspark from pip). Build the base natively first: PLATFORM=linux/arm64 TAG=... sh ../build.sh
ARG BASE=prophet-batch-examples/walmart-spark:native
FROM eclipse-temurin:21-jre AS jre
FROM ${BASE}
USER root
COPY --from=jre /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk PATH=/opt/java/openjdk/bin:$PATH
RUN pip install --no-cache-dir pyspark==4.0.1
USER spark
