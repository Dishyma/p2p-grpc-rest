# Security Group for Basic Access (for debugging)
resource "aws_security_group" "sg_basic" {
  name        = "p2p-sg-basic"
  description = "Allow all inbound traffic for debugging"
  vpc_id      = aws_vpc.main.id

  # Allow all inbound traffic
  ingress {
    description = "All inbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "p2p-sg-basic" }
}

# Security Group for Directory Server
resource "aws_security_group" "sg_directory" {
  name        = "p2p-sg-directory"
  description = "Allow HTTP for directory server and SSH access"
  vpc_id      = aws_vpc.main.id

  # SSH access
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Directory REST
  ingress {
    description = "Directory REST"
    from_port   = var.directory_server_port
    to_port     = var.directory_server_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP for debugging
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "p2p-sg-directory" }
}

# Security Group for Peers
resource "aws_security_group" "sg_peers" {
  name        = "p2p-sg-peers"
  description = "Allow gRPC and REST for peers and SSH access"
  vpc_id      = aws_vpc.main.id

  # SSH access
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # gRPC port
  ingress {
    description = "gRPC"
    from_port   = 50051
    to_port     = 50051
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # REST base range for convenience (8001-8099)
  ingress {
    description = "Peer REST range"
    from_port   = var.peer_rest_base_port
    to_port     = var.peer_rest_base_port + 99
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP for debugging
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # All ports from same security group (for inter-peer communication)
  ingress {
    description = "All internal traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "p2p-sg-peers" }
}

# Security Group for RDS
resource "aws_security_group" "sg_rds" {
  name        = "p2p-sg-rds"
  description = "DB access from directory server and direct access"
  vpc_id      = aws_vpc.main.id

  # Access from directory server security group
  ingress {
    description     = "Postgres from directory server"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_directory.id]
  }

  # Direct access from anywhere (for debugging)
  ingress {
    description = "Postgres direct access"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "p2p-sg-rds" }
}
