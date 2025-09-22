data "aws_ami" "amazon_linux2" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# Directory Server EC2
resource "aws_instance" "directory" {
  ami                         = data.aws_ami.amazon_linux2.id
  instance_type               = var.instance_type_default
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.sg_directory.id]
  key_name                    = var.key_name
  associate_public_ip_address = true

  # Esperar a que la base de datos esté disponible
  depends_on = [aws_db_instance.postgres]

  user_data = templatefile("${path.module}/user_data/directory_server.sh", {
    db_url       = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
    git_repo_url = var.git_repo_url
    git_branch   = var.git_branch
  })

  tags = { Name = "p2p-directory-server" }
}

# Peers EC2 (count)
resource "aws_instance" "peer" {
  count                       = var.peers_count
  ami                         = data.aws_ami.amazon_linux2.id
  instance_type               = var.instance_type_default
  subnet_id                   = aws_subnet.public[(count.index + 1) % length(aws_subnet.public)].id
  vpc_security_group_ids      = [aws_security_group.sg_peers.id]
  key_name                    = var.key_name
  associate_public_ip_address = true

  # Esperar a que la base de datos y el directory server estén disponibles
  depends_on = [
    aws_db_instance.postgres,
    aws_instance.directory
  ]

  user_data = templatefile("${path.module}/user_data/peer.sh", {
    git_repo_url          = var.git_repo_url
    git_branch            = var.git_branch
    peer_name             = "peer_${count.index + 1}"
    peer_password         = "peer123" # for demo
    peer_ip               = "0.0.0.0"
    grpc_port             = 50051
    rest_port             = var.peer_rest_base_port + count.index
    files_directory       = "/home/ec2-user/files"
    directory_server_url  = "http://${aws_instance.directory.public_ip}:${var.directory_server_port}/api/v1"
    heartbeat_interval    = 30
    log_level             = "INFO"
  })

  root_block_device {
    volume_size = 16
  }

  tags = { Name = "p2p-peer-${count.index + 1}" }
}
