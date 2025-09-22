variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.20.1.0/24", "10.20.2.0/24"]
}

variable "key_name" {
  type        = string
  description = "Existing EC2 key pair name for SSH"
}

variable "git_repo_url" {
  type        = string
  description = "Git repo URL to clone this project on instances"
}

variable "git_branch" {
  type    = string
  default = "main"
}

variable "db_name" {
  type    = string
  default = "p2pdb"
}

variable "db_username" {
  type    = string
  default = "p2puser"
}

variable "db_password" {
  type        = string
  description = "DB password"
  sensitive   = true
}

variable "instance_type_default" {
  type    = string
  default = "t3.micro"
}

variable "peers_count" {
  type    = number
  default = 2
}

variable "peer_rest_base_port" {
  type    = number
  default = 8001
}

variable "directory_server_port" {
  type    = number
  default = 8080
}
