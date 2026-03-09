# ============================================================================
# MLflow Tracking Server Outputs
# ============================================================================

output "mlflow_tracking_uri" {
  description = "MLflow tracking URI (použij v MLFLOW_TRACKING_URI)"
  value       = var.enable_https ? "https://${aws_lb.mlflow.dns_name}" : "http://${aws_lb.mlflow.dns_name}"
}

output "mlflow_alb_dns" {
  description = "ALB DNS meno"
  value       = aws_lb.mlflow.dns_name
}

output "mlflow_alb_arn" {
  description = "ALB ARN"
  value       = aws_lb.mlflow.arn
}

# ============================================================================
# S3 Outputs
# ============================================================================

output "mlflow_s3_bucket_name" {
  description = "S3 bucket pre MLflow artifacts"
  value       = aws_s3_bucket.mlflow_artifacts.id
}

output "mlflow_s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.mlflow_artifacts.arn
}

# ============================================================================
# RDS Outputs
# ============================================================================

output "mlflow_db_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.mlflow.endpoint
}

output "mlflow_db_name" {
  description = "Database name"
  value       = aws_db_instance.mlflow.db_name
}

output "mlflow_db_secret_arn" {
  description = "Secrets Manager ARN pre DB credentials"
  value       = aws_secretsmanager_secret.mlflow_db.arn
  sensitive   = true
}

# ============================================================================
# ECS Outputs
# ============================================================================

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.mlflow.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.mlflow.arn
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.mlflow.name
}

output "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.ecs_task.arn
}

# ============================================================================
# VPC Outputs
# ============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

# ============================================================================
# Security Group Outputs
# ============================================================================

output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ECS tasks security group ID"
  value       = aws_security_group.ecs_tasks.id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

# ============================================================================
# Connection Information
# ============================================================================

output "connection_info" {
  description = "MLflow connection information"
  value = {
    tracking_uri = var.enable_https ? "https://${aws_lb.mlflow.dns_name}" : "http://${aws_lb.mlflow.dns_name}"
    s3_bucket    = aws_s3_bucket.mlflow_artifacts.id
    db_endpoint  = aws_db_instance.mlflow.endpoint
    region       = var.aws_region
  }
}

# ============================================================================
# Cost Estimation
# ============================================================================

output "estimated_monthly_cost" {
  description = "Odhadované mesačné náklady (USD)"
  value = {
    fargate_cpu_memory = "~${var.mlflow_cpu / 256 * 5 * var.mlflow_desired_count} USD (${var.mlflow_cpu} CPU, ${var.mlflow_memory} MB)"
    rds                = "~${var.db_instance_class == "db.t3.micro" ? "15" : "30"} USD (${var.db_instance_class})"
    nat_gateway        = "~${length(var.availability_zones) * 35} USD (${length(var.availability_zones)} NAT GWs)"
    alb                = "~20 USD"
    s3                 = "~5 USD (depends on usage)"
    total              = "~70-100 USD/month"
  }
}
