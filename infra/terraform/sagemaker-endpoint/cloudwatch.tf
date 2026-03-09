# ============================================================================
# CloudWatch Alarms pre SageMaker Endpoint
# ============================================================================

# SNS Topic pre alarm notifications (optional)
resource "aws_sns_topic" "endpoint_alarms" {
  count = var.enable_cloudwatch_alarms && var.alarm_email != "" ? 1 : 0

  name = "${var.project_name}-${var.environment}-endpoint-alarms"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-endpoint-alarms"
    }
  )
}

resource "aws_sns_topic_subscription" "endpoint_alarms_email" {
  count = var.enable_cloudwatch_alarms && var.alarm_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.endpoint_alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# ============================================================================
# Alarm: Model Invocation Errors (4XX)
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "invocation_4xx_errors" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-endpoint-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Invocation4XXErrors"
  namespace           = "AWS/SageMaker"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 10 # More than 10 errors in 5 minutes
  alarm_description   = "Endpoint has too many 4XX invocation errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.main.name
    VariantName  = var.variant_name
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.endpoint_alarms[0].arn] : []

  tags = var.tags
}

# ============================================================================
# Alarm: Model Invocation Errors (5XX)
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "invocation_5xx_errors" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-endpoint-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Invocation5XXErrors"
  namespace           = "AWS/SageMaker"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 5 # More than 5 errors in 5 minutes
  alarm_description   = "Endpoint has too many 5XX invocation errors (server-side)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.main.name
    VariantName  = var.variant_name
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.endpoint_alarms[0].arn] : []

  tags = var.tags
}

# ============================================================================
# Alarm: Model Latency (High)
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "model_latency" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-endpoint-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelLatency"
  namespace           = "AWS/SageMaker"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = var.model_latency_threshold_ms
  alarm_description   = "Endpoint model latency is too high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.main.name
    VariantName  = var.variant_name
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.endpoint_alarms[0].arn] : []

  tags = var.tags
}

# ============================================================================
# Alarm: Invocation Throttles (Capacity Issues)
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "invocation_throttles" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-endpoint-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ModelSetupTime"
  namespace           = "AWS/SageMaker"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Endpoint experiencing throttling (capacity issues)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.main.name
    VariantName  = var.variant_name
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.endpoint_alarms[0].arn] : []

  tags = var.tags
}

# ============================================================================
# Alarm: CPU Utilization (High)
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "cpu_utilization" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-endpoint-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "/aws/sagemaker/Endpoints"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 80 # 80% CPU
  alarm_description   = "Endpoint CPU utilization is too high (consider scaling)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.main.name
    VariantName  = var.variant_name
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.endpoint_alarms[0].arn] : []

  tags = var.tags
}

# ============================================================================
# Alarm: Memory Utilization (High)
# ============================================================================

resource "aws_cloudwatch_metric_alarm" "memory_utilization" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-endpoint-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "MemoryUtilization"
  namespace           = "/aws/sagemaker/Endpoints"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 85 # 85% memory
  alarm_description   = "Endpoint memory utilization is too high (OOM risk)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.main.name
    VariantName  = var.variant_name
  }

  alarm_actions = var.alarm_email != "" ? [aws_sns_topic.endpoint_alarms[0].arn] : []

  tags = var.tags
}

# ============================================================================
# CloudWatch Dashboard (optional)
# ============================================================================

resource "aws_cloudwatch_dashboard" "endpoint" {
  count = var.enable_cloudwatch_alarms ? 1 : 0

  dashboard_name = "${var.project_name}-${var.environment}-endpoint"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/SageMaker", "Invocations", { stat = "Sum", label = "Total Invocations" }],
            [".", "Invocation4XXErrors", { stat = "Sum", label = "4XX Errors" }],
            [".", "Invocation5XXErrors", { stat = "Sum", label = "5XX Errors" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Endpoint Invocations & Errors"
          dimensions = {
            EndpointName = aws_sagemaker_endpoint.main.name
            VariantName  = var.variant_name
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/SageMaker", "ModelLatency", { stat = "Average", label = "Avg Latency" }],
            ["...", { stat = "p50", label = "p50 Latency" }],
            ["...", { stat = "p99", label = "p99 Latency" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Model Latency"
          yAxis = {
            left = {
              label = "Milliseconds"
            }
          }
          dimensions = {
            EndpointName = aws_sagemaker_endpoint.main.name
            VariantName  = var.variant_name
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["/aws/sagemaker/Endpoints", "CPUUtilization", { stat = "Average", label = "CPU %" }],
            [".", "MemoryUtilization", { stat = "Average", label = "Memory %" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Resource Utilization"
          yAxis = {
            left = {
              label = "Percent"
              max   = 100
            }
          }
          dimensions = {
            EndpointName = aws_sagemaker_endpoint.main.name
            VariantName  = var.variant_name
          }
        }
      }
    ]
  })
}
