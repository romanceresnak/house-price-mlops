variable "aws_region" {
  description = "AWS región pre MLflow server"
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

variable "owner" {
  description = "Vlastník infraštruktúry"
  type        = string
  default     = "Roman Ceresnak"
}

# ============================================================================
# VPC Configuration
# ============================================================================

variable "vpc_cidr" {
  description = "CIDR block pre VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones pre deployment"
  type        = list(string)
  default     = ["eu-west-1a", "eu-west-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR bloky pre public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR bloky pre private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

# ============================================================================
# RDS Configuration
# ============================================================================

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Názov PostgreSQL databázy"
  type        = string
  default     = "mlflow"
}

variable "db_username" {
  description = "Master username pre RDS"
  type        = string
  default     = "mlflow_admin"
  sensitive   = true
}

variable "db_password" {
  description = "Master password pre RDS (nastaviť cez tfvars alebo env variable)"
  type        = string
  sensitive   = true
}

variable "db_allocated_storage" {
  description = "Veľkosť storage pre RDS (GB)"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximálna veľkosť storage pre autoscaling (GB)"
  type        = number
  default     = 100
}

variable "db_backup_retention_days" {
  description = "Počet dní pre backup retention"
  type        = number
  default     = 7
}

# ============================================================================
# ECS / Fargate Configuration
# ============================================================================

variable "mlflow_image" {
  description = "Docker image pre MLflow server"
  type        = string
  default     = "ghcr.io/mlflow/mlflow:latest"
}

variable "mlflow_cpu" {
  description = "CPU jednotky pre MLflow task (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 512
}

variable "mlflow_memory" {
  description = "Pamäť pre MLflow task v MB (512, 1024, 2048, 3072, 4096, ...)"
  type        = number
  default     = 1024
}

variable "mlflow_desired_count" {
  description = "Počet MLflow tasks"
  type        = number
  default     = 1
}

variable "mlflow_port" {
  description = "Port pre MLflow server"
  type        = number
  default     = 5000
}

# ============================================================================
# ALB Configuration
# ============================================================================

variable "enable_https" {
  description = "Povoliť HTTPS na ALB (vyžaduje ACM certifikát)"
  type        = bool
  default     = false
}

variable "certificate_arn" {
  description = "ARN ACM certifikátu pre HTTPS (ak enable_https = true)"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Doménové meno pre MLflow server (voliteľné)"
  type        = string
  default     = ""
}

# ============================================================================
# S3 Configuration
# ============================================================================

variable "s3_bucket_name" {
  description = "Názov S3 bucketu pre MLflow artifacts (musí byť unique)"
  type        = string
  default     = ""
}

variable "s3_force_destroy" {
  description = "Povoliť destroy S3 bucketu aj s obsahom"
  type        = bool
  default     = false
}

# ============================================================================
# Tagging
# ============================================================================

variable "additional_tags" {
  description = "Dodatočné tagy pre resources"
  type        = map(string)
  default     = {}
}
