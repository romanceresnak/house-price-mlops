variable "aws_region" {
  description = "AWS región"
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Názov projektu"
  type        = string
  default     = "house-price-mlops"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "ecr_repository_name" {
  description = "Názov ECR repository"
  type        = string
  default     = "house-price-mlops"
}

variable "s3_data_bucket_name" {
  description = "Názov S3 bucketu pre training data"
  type        = string
  default     = ""  # Auto-generated if empty
}

variable "s3_model_bucket_name" {
  description = "Názov S3 bucketu pre model artifacts"
  type        = string
  default     = ""  # Auto-generated if empty
}

variable "s3_force_destroy" {
  description = "Povoliť destroy S3 bucketu aj s obsahom"
  type        = bool
  default     = false
}

variable "mlflow_s3_bucket_arn" {
  description = "ARN MLflow S3 artifacts bucketu (z MLflow terraform)"
  type        = string
  default     = ""
}
