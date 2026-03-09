# ============================================================================
# Random suffix pre unique S3 bucket name
# ============================================================================

resource "random_string" "s3_suffix" {
  length  = 8
  special = false
  upper   = false
}

# ============================================================================
# S3 Bucket pre MLflow Artifacts
# ============================================================================

resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = var.s3_bucket_name != "" ? var.s3_bucket_name : "${var.project_name}-${var.environment}-mlflow-artifacts-${random_string.s3_suffix.result}"

  force_destroy = var.s3_force_destroy

  tags = {
    Name        = "MLflow Artifacts"
    Environment = var.environment
  }
}

# ============================================================================
# S3 Bucket Versioning
# ============================================================================

resource "aws_s3_bucket_versioning" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ============================================================================
# S3 Bucket Encryption
# ============================================================================

resource "aws_s3_bucket_server_side_encryption_configuration" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ============================================================================
# S3 Bucket Public Access Block
# ============================================================================

resource "aws_s3_bucket_public_access_block" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================================================================
# S3 Bucket Lifecycle Policy (optional - pre cost optimization)
# ============================================================================

resource "aws_s3_bucket_lifecycle_configuration" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  rule {
    id     = "transition-old-artifacts"
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

  rule {
    id     = "delete-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ============================================================================
# S3 Bucket Policy (umožní prístup z ECS tasks)
# ============================================================================

data "aws_iam_policy_document" "mlflow_artifacts_policy" {
  statement {
    sid    = "AllowMLflowAccess"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.ecs_task_execution.arn, aws_iam_role.ecs_task.arn]
    }

    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]

    resources = [
      aws_s3_bucket.mlflow_artifacts.arn,
      "${aws_s3_bucket.mlflow_artifacts.arn}/*"
    ]
  }
}

resource "aws_s3_bucket_policy" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id
  policy = data.aws_iam_policy_document.mlflow_artifacts_policy.json
}
