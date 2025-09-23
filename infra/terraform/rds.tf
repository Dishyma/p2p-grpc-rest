resource "aws_db_subnet_group" "p2p" {
  name       = "p2p-db-subnet-group"
  subnet_ids = [for s in aws_subnet.public : s.id]
  tags = { Name = "p2p-db-subnet-group" }
}

resource "aws_db_instance" "postgres" {
  identifier              = "p2p-postgres"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  username                = var.db_username
  password                = var.db_password
  db_name                 = var.db_name
  port                    = 5432
  publicly_accessible     = true
  vpc_security_group_ids  = [aws_security_group.sg_rds.id]
  db_subnet_group_name    = aws_db_subnet_group.p2p.name
  skip_final_snapshot     = true
  deletion_protection     = false
  backup_retention_period = 0
  tags = { Name = "p2p-postgres" }
}
