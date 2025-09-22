#!/bin/bash
set -euo pipefail

# Install dependencies
amazon-linux-extras install docker -y || yum install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user || true

yum install -y git curl

# Env from Terraform
git_repo_url="${git_repo_url}"
git_branch="${git_branch}"
peer_name="${peer_name}"
peer_password="${peer_password}"
peer_ip="${peer_ip}"
grpc_download_port="${grpc_download_port}"
grpc_upload_port="${grpc_upload_port}"
grpc_list_port="${grpc_list_port}"
rest_port="${rest_port}"
files_directory="${files_directory}"
directory_server_url="${directory_server_url}"
heartbeat_interval="${heartbeat_interval}"
log_level="${log_level}"
peer_friend_primary_grpc="${peer_friend_primary_grpc}"
peer_friend_backup_grpc="${peer_friend_backup_grpc}"

# Clone repo
cd /home/ec2-user
sudo -u ec2-user git clone -b "$git_branch" "$git_repo_url" repo || true
cd repo

# Build and run peer container
/usr/bin/docker build -f Dockerfile.peer -t p2p-peer .

# Stop any existing container
/usr/bin/docker rm -f p2p-peer || true

# Prepare files directory
mkdir -p "$files_directory"
chown ec2-user:ec2-user "$files_directory"

# Initialize PEER_IP with the value from terraform
PEER_IP="$peer_ip"

# Resolve public IP if not provided or set to 0.0.0.0
if [ -z "$PEER_IP" ] || [ "$PEER_IP" = "0.0.0.0" ]; then
  META_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo "")
  if [ -n "$META_IP" ]; then
    PEER_IP="$META_IP"
  fi
fi

# Wait for directory server to be available
echo "Waiting for directory server to be available at: $directory_server_url"
# Extract base URL and create health check URL
BASE_URL=$(echo "$directory_server_url" | sed 's|/api/v1.*||')
HEALTH_URL="$BASE_URL/api/v1/health"
for i in {1..60}; do
  if curl -f -s "$HEALTH_URL" > /dev/null 2>&1 || curl -f -s "$BASE_URL" > /dev/null 2>&1; then
    echo "Directory server is available!"
    break
  fi
  echo "Attempt $i/60: Directory server not available yet (tried $HEALTH_URL), waiting 10 seconds..."
  sleep 10
done

# Run container
/usr/bin/docker run -d \
  --name p2p-peer \
  -p ${grpc_download_port}:${grpc_download_port} \
  -p ${grpc_upload_port}:${grpc_upload_port} \
  -p ${grpc_list_port}:${grpc_list_port} \
  -p ${rest_port}:${rest_port} \
  -e PEER_NAME="$peer_name" \
  -e PEER_PASSWORD="$peer_password" \
  -e PEER_IP="$PEER_IP" \
  -e GRPC_DOWNLOAD_PORT="$grpc_download_port" \
  -e GRPC_UPLOAD_PORT="$grpc_upload_port" \
  -e GRPC_LIST_PORT="$grpc_list_port" \
  -e REST_PORT="$rest_port" \
  -e FILES_DIRECTORY="$files_directory" \
  -e DIRECTORY_SERVER_URL="$directory_server_url" \
  -e HEARTBEAT_INTERVAL="$heartbeat_interval" \
  -e LOG_LEVEL="$log_level" \
  -e PEER_FRIEND_PRIMARY_GRPC="$peer_friend_primary_grpc" \
  -e PEER_FRIEND_BACKUP_GRPC="$peer_friend_backup_grpc" \
  -v "$files_directory":"$files_directory" \
  p2p-peer
