output "api_url" {
  value = "http://${aws_instance.test_server.public_ip}:8080"
}

output "lambda_name" {
  value = aws_lambda_function.telemetry.function_name
}

output "image_tested" {
  value = local.image_to_test
}
