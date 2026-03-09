# ============================================================================
# SageMaker Model Outputs
# ============================================================================

output "model_name" {
  description = "Názov SageMaker model"
  value       = aws_sagemaker_model.main.name
}

output "model_arn" {
  description = "ARN SageMaker model"
  value       = aws_sagemaker_model.main.arn
}

# ============================================================================
# Endpoint Configuration Outputs
# ============================================================================

output "endpoint_config_name" {
  description = "Názov endpoint configuration"
  value       = aws_sagemaker_endpoint_configuration.main.name
}

output "endpoint_config_arn" {
  description = "ARN endpoint configuration"
  value       = aws_sagemaker_endpoint_configuration.main.arn
}

# ============================================================================
# Endpoint Outputs
# ============================================================================

output "endpoint_name" {
  description = "Názov SageMaker endpoint"
  value       = aws_sagemaker_endpoint.main.name
}

output "endpoint_arn" {
  description = "ARN SageMaker endpoint"
  value       = aws_sagemaker_endpoint.main.arn
}

output "endpoint_url" {
  description = "HTTPS URL pre endpoint invocations"
  value       = "https://runtime.sagemaker.${var.aws_region}.amazonaws.com/endpoints/${aws_sagemaker_endpoint.main.name}/invocations"
}

# ============================================================================
# Instance Configuration
# ============================================================================

output "instance_type" {
  description = "Instance type používaný pre endpoint"
  value       = var.instance_type
}

output "instance_count" {
  description = "Počiatočný počet instancií"
  value       = var.initial_instance_count
}

# ============================================================================
# Auto-scaling Outputs
# ============================================================================

output "autoscaling_enabled" {
  description = "Je auto-scaling enabled?"
  value       = var.enable_autoscaling
}

output "autoscaling_min_instances" {
  description = "Minimálny počet instancií (ak auto-scaling enabled)"
  value       = var.enable_autoscaling ? var.min_instance_count : null
}

output "autoscaling_max_instances" {
  description = "Maximálny počet instancií (ak auto-scaling enabled)"
  value       = var.enable_autoscaling ? var.max_instance_count : null
}

# ============================================================================
# Monitoring Outputs
# ============================================================================

output "data_capture_enabled" {
  description = "Je data capture enabled?"
  value       = var.enable_data_capture
}

output "data_capture_bucket" {
  description = "S3 bucket pre captured data"
  value       = var.enable_data_capture ? aws_s3_bucket.data_capture[0].id : null
}

output "cloudwatch_dashboard_url" {
  description = "URL CloudWatch dashboard"
  value       = var.enable_cloudwatch_alarms ? "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.endpoint[0].dashboard_name}" : null
}

output "sns_topic_arn" {
  description = "ARN SNS topic pre alarms"
  value       = var.enable_cloudwatch_alarms && var.alarm_email != "" ? aws_sns_topic.endpoint_alarms[0].arn : null
}

# ============================================================================
# Quick Reference
# ============================================================================

output "quick_reference" {
  description = "Quick reference pre endpoint usage"
  value = {
    endpoint_name  = aws_sagemaker_endpoint.main.name
    endpoint_url   = "https://runtime.sagemaker.${var.aws_region}.amazonaws.com/endpoints/${aws_sagemaker_endpoint.main.name}/invocations"
    instance_type  = var.instance_type
    instance_count = var.initial_instance_count
    aws_region     = var.aws_region
  }
}

# ============================================================================
# Test Commands
# ============================================================================

output "test_commands" {
  description = "Príkazy na testovanie endpoint"
  value = {
    invoke_endpoint = "aws sagemaker-runtime invoke-endpoint --endpoint-name ${aws_sagemaker_endpoint.main.name} --body '{\"data\": [[...]]}' --content-type application/json output.json --region ${var.aws_region}"
    describe_endpoint = "aws sagemaker describe-endpoint --endpoint-name ${aws_sagemaker_endpoint.main.name} --region ${var.aws_region}"
    check_metrics = "aws cloudwatch get-metric-statistics --namespace AWS/SageMaker --metric-name Invocations --dimensions Name=EndpointName,Value=${aws_sagemaker_endpoint.main.name} Name=VariantName,Value=${var.variant_name} --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Sum --region ${var.aws_region}"
  }
}
