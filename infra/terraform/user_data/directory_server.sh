#!/bin/bash
set -euo pipefail

# Install dependencies
amazon-linux-extras install docker -y || yum install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user || true

yum install -y git curl

# Env from Terraform
db_url="${db_url}"
git_repo_url="${git_repo_url}"
git_branch="${git_branch}"

# Clone repo
cd /home/ec2-user
sudo -u ec2-user git clone -b "$git_branch" "$git_repo_url" repo || true
cd repo

# Build and run directory server
/usr/bin/docker build -f Dockerfile.dir -t directory-server .

# Stop any existing container
/usr/bin/docker rm -f directory-server || true

# Run container
/usr/bin/docker run -d \
  --name directory-server \
  -p 8080:8080 \
  -e DATABASE_URL="$db_url" \
  -e SQL_ECHO=false \
  directory-server

# Wait for directory server to be ready
echo "Waiting for directory server to be ready..."
for i in {1..30}; do
  if curl -f -s http://localhost:8080/health > /dev/null 2>&1 || curl -f -s http://localhost:8080/ > /dev/null 2>&1; then
    echo "Directory server is ready!"
    break
  fi
  echo "Attempt $i/30: Directory server not ready yet, waiting 10 seconds..."
  sleep 10
done

# Enable simple firewall openness (optional, security groups already handle it)
