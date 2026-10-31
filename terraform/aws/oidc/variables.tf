variable "github_repo" {
  description = "Your repo, as owner/name"
  type        = string
}

variable "environment" {
  description = "The GitHub Environment for this account: qa, dev, stage, or prod"
  type        = string
}

variable "region" {
  type    = string
  default = "us-east-1"
}
