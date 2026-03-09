# ============================================================================
# SageMaker Model
# ============================================================================

resource "aws_sagemaker_model" "main" {
  name               = "${var.project_name}-${var.environment}-${var.model_name}"
  execution_role_arn = var.sagemaker_execution_role_arn

  primary_container {
    image          = var.ecr_image_uri
    model_data_url = var.model_data_url
    environment = {
      SAGEMAKER_PROGRAM          = "src/serve/inference.py"
      SAGEMAKER_SUBMIT_DIRECTORY = "/opt/ml/code"
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-${var.model_name}"
    }
  )
}

# ============================================================================
# SageMaker Endpoint Configuration
# ============================================================================

resource "aws_sagemaker_endpoint_configuration" "main" {
  name = "${var.project_name}-${var.environment}-endpoint-config"

  production_variants {
    variant_name           = var.variant_name
    model_name             = aws_sagemaker_model.main.name
    instance_type          = var.instance_type
    initial_instance_count = var.initial_instance_count
    initial_variant_weight = var.initial_variant_weight
  }

  # Data Capture Configuration (pre model monitoring)
  dynamic "data_capture_config" {
    for_each = var.enable_data_capture ? [1] : []
    content {
      enable_capture = true
      initial_sampling_percentage = var.data_capture_sampling_percentage

      destination_s3_uri = "s3://${aws_s3_bucket.data_capture[0].id}/data-capture"

      capture_options {
        capture_mode = "InputAndOutput"
      }

      capture_content_type_header {
        csv_content_types  = ["text/csv"]
        json_content_types = ["application/json"]
      }
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-endpoint-config"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# ============================================================================
# SageMaker Endpoint
# ============================================================================

resource "aws_sagemaker_endpoint" "main" {
  name                 = var.endpoint_name != "" ? var.endpoint_name : "${var.project_name}-${var.environment}-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.main.name

  tags = merge(
    var.tags,
    {
      Name = var.endpoint_name != "" ? var.endpoint_name : "${var.project_name}-${var.environment}-endpoint"
    }
  )

  lifecycle {
    # Prevent accidental deletion of production endpoint
    prevent_destroy = false # Set to true for production
  }
}

# ============================================================================
# S3 Bucket pre Data Capture (optional)
# ============================================================================

resource "aws_s3_bucket" "data_capture" {
  count = var.enable_data_capture ? 1 : 0

  bucket = "${var.project_name}-${var.environment}-endpoint-data-capture"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-endpoint-data-capture"
      Purpose     = "SageMaker Endpoint Data Capture"
    }
  )
}

resource "aws_s3_bucket_versioning" "data_capture" {
  count  = var.enable_data_capture ? 1 : 0
  bucket = aws_s3_bucket.data_capture[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_capture" {
  count  = var.enable_data_capture ? 1 : 0
  bucket = aws_s3_bucket.data_capture[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_capture" {
  count  = var.enable_data_capture ? 1 : 0
  bucket = aws_s3_bucket.data_capture[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy pre data capture (cleanup old data)
resource "aws_s3_bucket_lifecycle_configuration" "data_capture" {
  count  = var.enable_data_capture ? 1 : 0
  bucket = aws_s3_bucket.data_capture[0].id

  rule {
    id     = "delete-old-captures"
    status = "Enabled"

    expiration {
      days = 30 # Keep captures for 30 days
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}
