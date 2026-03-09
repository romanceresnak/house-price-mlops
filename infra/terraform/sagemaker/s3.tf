# ============================================================================
# Random suffix pre unique bucket names
# ============================================================================

resource "random_string" "s3_suffix" {
  length  = 8
  special = false
  upper   = false
}

# ============================================================================
# S3 Bucket pre Training Data
# ============================================================================

resource "aws_s3_bucket" "data" {
  bucket = var.s3_data_bucket_name != "" ? var.s3_data_bucket_name : "${var.project_name}-${var.environment}-data-${random_string.s3_suffix.result}"

  force_destroy = var.s3_force_destroy

  tags = {
    Name        = "SageMaker Training Data"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================================================================
# S3 Bucket pre Model Artifacts
# ============================================================================

resource "aws_s3_bucket" "models" {
  bucket = var.s3_model_bucket_name != "" ? var.s3_model_bucket_name : "${var.project_name}-${var.environment}-models-${random_string.s3_suffix.result}"

  force_destroy = var.s3_force_destroy

  tags = {
    Name        = "SageMaker Model Artifacts"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "models" {
  bucket = aws_s3_bucket.models.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy pre model artifacts
resource "aws_s3_bucket_lifecycle_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    id     = "transition-old-models"
    status = "Enabled"

    # Transition artifacts staršie než 90 dní do Glacier
    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    # Vymaž artifacts staršie než 365 dní
    expiration {
      days = 365
    }
  }
}
