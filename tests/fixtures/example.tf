variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

locals {
  common_tags = {
    Environment = var.environment
    CostCenter  = "governance"
    ManagedBy   = "terraform"
  }
}

provider "aws" {
  region = "us-east-1"
}

provider "azurerm" {
  features {}
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = var.instance_type

  tags = merge(local.common_tags, {
    Name = "uiao-web-server"
  })
}

resource "aws_security_group" "web_sg" {
  name        = "uiao-web-sg"
  description = "Security group for UIAO web server"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "uiao-web-sg"
  })
}

resource "azurerm_resource_group" "governance" {
  name     = "uiao-governance-rg"
  location = "usgovvirginia"

  tags = merge(local.common_tags, {
    FedRAMP = "Moderate"
  })
}

data "aws_caller_identity" "current" {}
