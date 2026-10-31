# A short-lived test environment: one Linux server and one Lambda function.
# The pipeline creates it, tests it, and destroys it.

terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "aws-qa-framework"
      Environment = var.environment
      Owner       = "qa"
      CostCenter  = "qa-testing"
    }
  }
}

# ---------- Which image to test ----------

data "aws_ami" "latest_rhel9" {
  most_recent = true
  owners      = ["309956199498"] # Red Hat

  filter {
    name   = "name"
    values = ["RHEL-9.*_HVM-*-x86_64-*-Hourly2-GP3"]
  }
}

locals {
  image_to_test = var.ami_id != "" ? var.ami_id : data.aws_ami.latest_rhel9.id
}

# ---------- Network: only the API port, and only from the test runner ----------

data "aws_vpc" "default" {
  default = true
}

resource "aws_security_group" "test_server" {
  name_prefix = "qa-test-server-"
  description = "API port from the test runner only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "API"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.runner_cidr]
  }

  egress {
    description = "Packages, Systems Manager, and the vulnerability feed"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------- The Linux server ----------

resource "aws_instance" "test_server" {
  ami                    = local.image_to_test
  instance_type          = var.instance_type
  iam_instance_profile   = var.instance_profile
  vpc_security_group_ids = [aws_security_group.test_server.id]

  # Safety net: if destroy never runs, the server still removes itself.
  instance_initiated_shutdown_behavior = "terminate"

  user_data = <<-EOT
    #!/bin/bash
    shutdown -h +${var.max_minutes}
    dnf install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
    systemctl enable --now amazon-ssm-agent
  EOT

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  root_block_device {
    encrypted = true
  }

  tags = {
    Name   = "qa-test-server-${var.environment}"
    QAScan = "true"
  }
}

# ---------- The Lambda function ----------

data "archive_file" "telemetry" {
  type        = "zip"
  output_path = "${path.module}/telemetry.zip"

  source {
    filename = "sample_app/lambda_handler.py"
    content  = file("${path.module}/../../../sample_app/lambda_handler.py")
  }

  source {
    filename = "sample_app/telemetry.py"
    content  = file("${path.module}/../../../sample_app/telemetry.py")
  }
}

resource "aws_lambda_function" "telemetry" {
  function_name    = "qa-telemetry-${var.environment}"
  role             = var.lambda_role_arn
  runtime          = "python3.12"
  handler          = "sample_app.lambda_handler.handler"
  filename         = data.archive_file.telemetry.output_path
  source_code_hash = data.archive_file.telemetry.output_base64sha256
}
