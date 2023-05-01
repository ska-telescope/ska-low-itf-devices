FROM ubuntu:22.04 as builder

# For healthcheck
RUN apt-get update && apt-get install --no-install-recommends -y git ca-certificates

# Shallow clone of latest main as of 2023-05-01
RUN mkdir /app && \
    cd /app && \
    git init && \
    git remote add origin https://github.com/DMTF/Redfish-Mockup-Server.git && \
    git fetch --depth 1 origin 563bd952a51f8c555420faaeda12793012da0258 && \
    git checkout FETCH_HEAD


FROM python:3-slim

# Install python requirements
COPY --from=builder /app/*.py /app/requirements.txt /app/
RUN python3 -mpip install --no-cache-dir -r /app/requirements.txt

# copy the mockup files
COPY resources/redfish_mockups/enlogic_en6325 /app/mockup

# Env settings
WORKDIR /app
ENTRYPOINT ["python3", "/app/redfishMockupServer.py", "--host", "0.0.0.0", "--port", "8000", "--dir", "mockup"]
