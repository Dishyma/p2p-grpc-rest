# Main Terraform configuration for P2P gRPC REST system
# This file orchestrates all the infrastructure components

# Data sources and locals
locals {
  common_tags = {
    Project     = "p2p-grpc-rest"
    Environment = "demo"
    ManagedBy   = "terraform"
  }
}

# Apply common tags to all resources using a null_resource
resource "null_resource" "common_tags" {
  # This is a workaround for aws_default_tags not being available
  # Tags will be applied manually in each resource
}
