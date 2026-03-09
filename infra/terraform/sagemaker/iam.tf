# ============================================================================
# SageMaker Execution Role
# ============================================================================

resource "aws_iam_role" "sagemaker_execution" {
  name_prefix = "${var.project_name}-${var.environment}-sagemaker-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-sagemaker-execution-role"
  }
}

# ============================================================================
# Attach AWS Managed Policies
# ============================================================================

# SageMaker Full Access
resource "aws_iam_role_policy_attachment" "sagemaker_full_access" {
  role       = aws_iam_role.sagemaker_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

# ============================================================================
# Custom Policies
# ============================================================================

# S3 Access Policy
resource "aws_iam_role_policy" "sagemaker_s3_access" {
  name_prefix = "s3-access-"
  role        = aws_iam_role.sagemaker_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = concat(
          [
            aws_s3_bucket.data.arn,
            "${aws_s3_bucket.data.arn}/*",
            aws_s3_bucket.models.arn,
            "${aws_s3_bucket.models.arn}/*"
          ],
          var.mlflow_s3_bucket_arn != "" ? [
            var.mlflow_s3_bucket_arn,
            "${var.mlflow_s3_bucket_arn}/*"
          ] : []
        )
      }
    ]
  })
}

# ECR Access Policy
resource "aws_iam_role_policy" "sagemaker_ecr_access" {
  name_prefix = "ecr-access-"
  role        = aws_iam_role.sagemaker_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Logs Policy
resource "aws_iam_role_policy" "sagemaker_cloudwatch" {
  name_prefix = "cloudwatch-logs-"
  role        = aws_iam_role.sagemaker_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/sagemaker/*"
      }
    ]
  })
}

# VPC Access (ak SageMaker training beží vo VPC)
resource "aws_iam_role_policy" "sagemaker_vpc_access" {
  name_prefix = "vpc-access-"
  role        = aws_iam_role.sagemaker_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:CreateNetworkInterfacePermission",
          "ec2:DeleteNetworkInterface",
          "ec2:DeleteNetworkInterfacePermission",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeVpcs",
          "ec2:DescribeDhcpOptions",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups"
        ]
        Resource = "*"
      }
    ]
  })
}
