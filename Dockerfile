FROM python:3.12-slim

# Install dependencies for Go
RUN apt-get update && \
    apt-get install -y wget && \
    apt-get install -y build-essential && \
    apt-get clean

# Install Go
RUN wget https://dl.google.com/go/go1.23.2.linux-arm64.tar.gz && \
    tar -C /usr/local -xzf go1.23.2.linux-arm64.tar.gz && \
    rm go1.23.2.linux-arm64.tar.gz

# Set up Go environment variables
ENV GOROOT=/usr/local/go
ENV GOPATH=$HOME/go
ENV PATH=$GOPATH/bin:$GOROOT/bin:$PATH

# Setup flask app
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:80"]