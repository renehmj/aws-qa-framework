# Copy these into GitHub Environment variables. See docs/OIDC_SETUP.md.

output "QA_READONLY_ROLE_ARN" {
  value = aws_iam_role.readonly.arn
}

output "QA_TEST_ENV_ROLE_ARN" {
  value = aws_iam_role.test_env.arn
}

output "QA_LAMBDA_ROLE_ARN" {
  value = aws_iam_role.test_function.arn
}

output "QA_SSM_BUCKET" {
  value = aws_s3_bucket.ssm_transfer.bucket
}

output "AWS_ACCOUNT_ID" {
  value = local.account_id
}
