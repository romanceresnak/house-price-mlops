# ============================================================================
# SageMaker Outputs
# ============================================================================

output "sagemaker_execution_role_arn" {
  description = "ARN SageMaker execution role"
  value       = aws_iam_role.sagemaker_execution.arn
}

output "sagemaker_execution_role_name" {
  description = "Názov SageMaker execution role"
  value       = aws_iam_role.sagemaker_execution.name
}

# ============================================================================
# S3 Outputs
# ============================================================================

output "s3_data_bucket_name" {
  description = "Názov S3 bucketu pre training data"
  value       = aws_s3_bucket.data.id
}

output "s3_data_bucket_arn" {
  description = "ARN S3 bucketu pre training data"
  value       = aws_s3_bucket.data.arn
}

output "s3_model_bucket_name" {
  description = "Názov S3 bucketu pre model artifacts"
  value       = aws_s3_bucket.models.id
}

output "s3_model_bucket_arn" {
  description = "ARN S3 bucketu pre model artifacts"
  value       = aws_s3_bucket.models.arn
}

# ============================================================================
# ECR Outputs
# ============================================================================

output "ecr_repository_url" {
  description = "URL ECR repository"
  value       = aws_ecr_repository.training.repository_url
}

output "ecr_repository_arn" {
  description = "ARN ECR repository"
  value       = aws_ecr_repository.training.arn
}

output "ecr_repository_name" {
  description = "Názov ECR repository"
  value       = aws_ecr_repository.training.name
}

# ============================================================================
# Quick Reference
# ============================================================================

output "quick_reference" {
  description = "Quick reference pre SageMaker training"
  value = {
    role_arn        = aws_iam_role.sagemaker_execution.arn
    data_bucket     = aws_s3_bucket.data.id
    model_bucket    = aws_s3_bucket.models.id
    ecr_url         = aws_ecr_repository.training.repository_url
    aws_region      = var.aws_region
  }
}

# ============================================================================
# Commands
# ============================================================================

output "useful_commands" {
  description = "Užitočné príkazy"
  value = {
    upload_data = "aws s3 cp data/train.csv s3://${aws_s3_bucket.data.id}/data/"
    login_ecr   = "aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.training.repository_url}"
    push_image  = "./scripts/build_and_push.sh ${var.aws_region} ${var.ecr_repository_name}"
    list_jobs   = "aws sagemaker list-training-jobs --region ${var.aws_region}"
  }
}
