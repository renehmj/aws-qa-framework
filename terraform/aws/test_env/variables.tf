variable "environment" {
  description = "Which account this is: qa, dev, or stage"
  type        = string
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "ami_id" {
  description = "Image to test. Empty means the latest RHEL 9."
  type        = string
  default     = ""
}

variable "instance_type" {
  type    = string
  default = "t3.medium"
}

variable "runner_cidr" {
  description = "The test runner's address, the only one allowed to reach the API"
  type        = string
}

variable "instance_profile" {
  description = "From terraform/aws/oidc"
  type        = string
  default     = "qa-test-server"
}

variable "lambda_role_arn" {
  description = "From terraform/aws/oidc"
  type        = string
}

variable "max_minutes" {
  description = "The server shuts itself down after this long"
  type        = number
  default     = 90
}
