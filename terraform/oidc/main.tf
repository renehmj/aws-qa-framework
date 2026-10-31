# One-time setup, once per AWS account. See docs/OIDC_SETUP.md.
# Lets one GitHub Environment, and nothing else, get short-lived credentials here.

terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
}

# ---------- Trust: which GitHub job can use these roles ----------

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "github_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Only this repo, and only this GitHub Environment.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:environment:${var.environment}"]
    }
  }
}

# ---------- Role 1: read-only. Runs the AWS and SCP tests ----------

resource "aws_iam_role" "readonly" {
  name                 = "qa-readonly"
  assume_role_policy   = data.aws_iam_policy_document.github_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "readonly" {
  statement {
    actions = [
      "cloudtrail:DescribeTrails",
      "cloudtrail:GetTrailStatus",
      "ec2:DescribeInstances",
      "ec2:DescribeSecurityGroups",
      "iam:GetAccountSummary",
      "iam:GetLoginProfile",
      "iam:ListMFADevices",
      "iam:ListUsers",
      "iam:SimulatePrincipalPolicy",
      "s3:GetBucketPublicAccessBlock",
      "s3:GetEncryptionConfiguration",
      "s3:ListAllMyBuckets",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "readonly" {
  role   = aws_iam_role.readonly.id
  policy = data.aws_iam_policy_document.readonly.json
}

# ---------- Role 2: builds and tests the short-lived test environment ----------

resource "aws_iam_role" "test_env" {
  name                 = "qa-test-env"
  assume_role_policy   = data.aws_iam_policy_document.github_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "test_env" {
  statement {
    sid = "BuildTheServer"
    actions = [
      "ec2:AuthorizeSecurityGroupEgress",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:CreateSecurityGroup",
      "ec2:CreateTags",
      "ec2:DeleteSecurityGroup",
      "ec2:Describe*",
      "ec2:RevokeSecurityGroupEgress",
      "ec2:RunInstances",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "DestroyOnlyOurServers"
    actions   = ["ec2:TerminateInstances", "ec2:ModifyInstanceAttribute"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Project"
      values   = ["aws-qa-framework"]
    }
  }

  statement {
    sid     = "PassOnlyOurRoles"
    actions = ["iam:PassRole", "iam:GetRole", "iam:GetInstanceProfile"]
    resources = [
      aws_iam_role.test_server.arn,
      aws_iam_role.test_function.arn,
      aws_iam_instance_profile.test_server.arn,
    ]
  }

  statement {
    sid       = "ManageOnlyOurFunction"
    actions   = ["lambda:*"]
    resources = ["arn:aws:lambda:${var.region}:${local.account_id}:function:qa-telemetry-*"]
  }

  statement {
    sid       = "ListFunctions"
    actions   = ["lambda:ListFunctions"]
    resources = ["*"]
  }

  statement {
    sid       = "ReachOnlyTaggedServers"
    actions   = ["ssm:StartSession"]
    resources = ["arn:aws:ec2:${var.region}:${local.account_id}:instance/*"]

    condition {
      test     = "StringEquals"
      variable = "ssm:resourceTag/QAScan"
      values   = ["true"]
    }
  }

  statement {
    sid       = "SessionDocument"
    actions   = ["ssm:StartSession"]
    resources = ["arn:aws:ssm:${var.region}::document/SSM-SessionManagerRunShell"]
  }

  statement {
    sid       = "EndOurSessions"
    actions   = ["ssm:GetConnectionStatus", "ssm:ResumeSession", "ssm:TerminateSession"]
    resources = ["*"]
  }

  statement {
    sid       = "AnsibleFileTransfer"
    actions   = ["s3:DeleteObject", "s3:GetObject", "s3:ListBucket", "s3:PutObject"]
    resources = [aws_s3_bucket.ssm_transfer.arn, "${aws_s3_bucket.ssm_transfer.arn}/*"]
  }
}

resource "aws_iam_role_policy" "test_env" {
  role   = aws_iam_role.test_env.id
  policy = data.aws_iam_policy_document.test_env.json
}

# ---------- What the test server and function run as ----------

data "aws_iam_policy_document" "ec2_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "test_server" {
  name               = "qa-test-server"
  assume_role_policy = data.aws_iam_policy_document.ec2_trust.json
}

resource "aws_iam_role_policy_attachment" "test_server_ssm" {
  role       = aws_iam_role.test_server.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "test_server_transfer" {
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:GetEncryptionConfiguration"]
    resources = [aws_s3_bucket.ssm_transfer.arn, "${aws_s3_bucket.ssm_transfer.arn}/*"]
  }
}

resource "aws_iam_role_policy" "test_server_transfer" {
  role   = aws_iam_role.test_server.id
  policy = data.aws_iam_policy_document.test_server_transfer.json
}

resource "aws_iam_instance_profile" "test_server" {
  name = "qa-test-server"
  role = aws_iam_role.test_server.name
}

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "test_function" {
  name               = "qa-test-function"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

resource "aws_iam_role_policy_attachment" "test_function_logs" {
  role       = aws_iam_role.test_function.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ---------- Bucket Ansible uses to move files through Systems Manager ----------

resource "aws_s3_bucket" "ssm_transfer" {
  bucket_prefix = "qa-ssm-transfer-"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "ssm_transfer" {
  bucket                  = aws_s3_bucket.ssm_transfer.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ssm_transfer" {
  bucket = aws_s3_bucket.ssm_transfer.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "ssm_transfer" {
  bucket = aws_s3_bucket.ssm_transfer.id

  rule {
    id     = "delete-after-one-day"
    status = "Enabled"

    filter {}

    expiration {
      days = 1
    }
  }
}
