output "directory_public_ip" {
  value = aws_instance.directory.public_ip
}

output "directory_url" {
  value = "http://${aws_instance.directory.public_ip}:${var.directory_server_port}"
}

output "peer_public_ips" {
  value = [for p in aws_instance.peer : p.public_ip]
}

output "peer_rest_urls" {
  value = [for idx, p in aws_instance.peer : "http://${p.public_ip}:${var.peer_rest_base_port + idx}"]
}

output "peer_grpc_endpoints" {
  value = [for p in aws_instance.peer : "${p.public_ip}:50051"]
}

output "directory_instance_id" {
  value = aws_instance.directory.id
}

output "peer_instance_ids" {
  value = [for p in aws_instance.peer : p.id]
}

# Database connection info for debugging
output "database_endpoint" {
  description = "PostgreSQL connection endpoint"
  value       = aws_db_instance.postgres.address
}

output "database_connection_string" {
  description = "Full database connection string for debugging"
  value       = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
  sensitive   = true
}

output "database_host" {
  description = "Database host for direct connection"
  value       = aws_db_instance.postgres.address
}

output "database_port" {
  description = "Database port"
  value       = 5432
}
