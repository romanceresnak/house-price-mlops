# ============================================================================
# SageMaker Endpoint Variables
# ============================================================================

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
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "prod"
}

# ============================================================================
# Model Configuration
# ============================================================================

variable "model_name" {
  description = "Názov SageMaker model"
  type        = string
  default     = "house-price-xgboost"
}

variable "model_data_url" {
  description = "S3 URL pre model artifacts (model.tar.gz). Musí byť nastavený manuálne alebo z training job output."
  type        = string
  default     = ""
}

variable "sagemaker_execution_role_arn" {
  description = "ARN SageMaker execution role (z sagemaker terraform output)"
  type        = string
}

variable "ecr_image_uri" {
  description = "URI Docker image v ECR (vrátane tagu)"
  type        = string
}

# ============================================================================
# Endpoint Configuration
# ============================================================================

variable "endpoint_name" {
  description = "Názov SageMaker endpoint. Ak prázdne, vygeneruje sa automaticky."
  type        = string
  default     = ""
}

variable "instance_type" {
  description = "Instance type pre endpoint (ml.t2.medium, ml.m5.large, etc.)"
  type        = string
  default     = "ml.t2.medium" # ~$0.065/hour, 2 vCPU, 4GB RAM
}

variable "initial_instance_count" {
  description = "Počiatočný počet instancií"
  type        = number
  default     = 1

  validation {
    condition     = var.initial_instance_count >= 1
    error_message = "Initial instance count must be at least 1"
  }
}

variable "variant_name" {
  description = "Názov production variant"
  type        = string
  default     = "AllTraffic"
}

variable "initial_variant_weight" {
  description = "Traffic weight pre production variant (1.0 = 100%)"
  type        = number
  default     = 1.0
}

# ============================================================================
# Auto-scaling Configuration
# ============================================================================

variable "enable_autoscaling" {
  description = "Enable auto-scaling pre endpoint"
  type        = bool
  default     = false
}

variable "min_instance_count" {
  description = "Minimálny počet instancií pre auto-scaling"
  type        = number
  default     = 1
}

variable "max_instance_count" {
  description = "Maximálny počet instancií pre auto-scaling"
  type        = number
  default     = 3
}

variable "target_invocations_per_instance" {
  description = "Cieľový počet invocations per instance (trigger pre scaling)"
  type        = number
  default     = 1000
}

# ============================================================================
# Monitoring & Alarms
# ============================================================================

variable "enable_data_capture" {
  description = "Enable data capture pre model monitoring"
  type        = bool
  default     = false
}

variable "data_capture_sampling_percentage" {
  description = "Percentuálny podiel requestov na capture (0-100)"
  type        = number
  default     = 100

  validation {
    condition     = var.data_capture_sampling_percentage >= 0 && var.data_capture_sampling_percentage <= 100
    error_message = "Sampling percentage must be between 0 and 100"
  }
}

variable "enable_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms pre endpoint"
  type        = bool
  default     = true
}

variable "alarm_email" {
  description = "Email pre CloudWatch alarm notifications"
  type        = string
  default     = ""
}

variable "model_latency_threshold_ms" {
  description = "Threshold pre ModelLatency alarm (milliseconds)"
  type        = number
  default     = 5000 # 5 seconds
}

variable "invocation_error_rate_threshold" {
  description = "Threshold pre Invocation4XXErrors rate alarm (percent)"
  type        = number
  default     = 5 # 5%
}

# ============================================================================
# Tags
# ============================================================================

variable "tags" {
  description = "Dodatočné tagy pre resources"
  type        = map(string)
  default     = {}
}
