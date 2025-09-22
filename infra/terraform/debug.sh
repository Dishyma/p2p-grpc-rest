#!/bin/bash
# Script de debugging para P2P Network
# Uso: ./debug.sh

echo "🔍 P2P Network Debugging Script"
echo "================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para verificar conectividad
check_connection() {
    local url=$1
    local description=$2

    echo -e "\n${YELLOW}Checking $description:${NC}"
    echo "URL: $url"

    if curl -s --max-time 10 -o /dev/null "$url"; then
        echo -e "${GREEN}✅ $description is responding${NC}"
        return 0
    else
        echo -e "${RED}❌ $description is not responding${NC}"
        return 1
    fi
}

# Función para verificar SSH
check_ssh() {
    local host=$1
    local description=$2

    echo -e "\n${YELLOW}Checking SSH to $description:${NC}"
    echo "Host: $host"

    if nc -z -w5 $host 22; then
        echo -e "${GREEN}✅ SSH port is open on $description${NC}"
        return 0
    else
        echo -e "${RED}❌ SSH port is closed on $description${NC}"
        return 1
    fi
}

# Función para verificar base de datos
check_database() {
    local host=$1
    local description=$2

    echo -e "\n${YELLOW}Checking Database on $description:${NC}"
    echo "Host: $host:5432"

    if nc -z -w5 $host 5432; then
        echo -e "${GREEN}✅ Database port is open on $description${NC}"
        return 0
    else
        echo -e "${RED}❌ Database port is closed on $description${NC}"
        return 1
    fi
}

echo -e "${YELLOW}Current Terraform outputs:${NC}"
echo "Run: terraform output"

echo -e "\n${YELLOW}Step 1: Checking basic connectivity...${NC}"
ping -c 3 8.8.8.8 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Internet connection is working${NC}"
else
    echo -e "${RED}❌ No internet connection${NC}"
fi

echo -e "\n${YELLOW}Step 2: Checking instance connectivity...${NC}"
# Estas IPs necesitarías obtenerlas de terraform output o de tu configuración actual
DIRECTORY_IP="54.226.171.26"
PEER1_IP="98.86.220.128"
PEER2_IP="3.88.201.254"

check_connection "http://$DIRECTORY_IP:8080/api/v1/peers" "Directory Server API"
check_connection "http://$PEER1_IP:8001" "Peer 1 REST API"
check_connection "http://$PEER2_IP:8002" "Peer 2 REST API"

echo -e "\n${YELLOW}Step 3: Checking ports...${NC}"
check_ssh "$DIRECTORY_IP" "Directory Server"
check_ssh "$PEER1_IP" "Peer 1"
check_ssh "$PEER2_IP" "Peer 2"

# Database endpoint - necesitarías obtenerlo de terraform output
DB_HOST="db-CF2HUVRECJ23BJBJELGMXHU2HM.us-east-1.rds.amazonaws.com"
check_database "$DB_HOST" "Database"

echo -e "\n${YELLOW}Step 4: Summary${NC}"
echo "If you see any ❌ above, here's what to check:"
echo "1. Are your instances running? (Check AWS Console)"
echo "2. Are security groups applied? (Check terraform apply completed)"
echo "3. Are containers running on instances? (SSH and check docker ps)"
echo "4. Check logs: docker logs <container_name>"

echo -e "\n${YELLOW}Useful commands:${NC}"
echo "terraform output                          # See all endpoints"
echo "aws ec2 describe-instances                # Check instance status"
echo "ssh -i ~/.ssh/my-ec2-keypair.pem ec2-user@<IP>  # SSH to instance"
