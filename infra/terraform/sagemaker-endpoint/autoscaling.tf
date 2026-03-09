# ============================================================================
# Auto-scaling pre SageMaker Endpoint
# ============================================================================

# Auto-scaling Target
resource "aws_appautoscaling_target" "sagemaker_endpoint" {
  count = var.enable_autoscaling ? 1 : 0

  max_capacity       = var.max_instance_count
  min_capacity       = var.min_instance_count
  resource_id        = "endpoint/${aws_sagemaker_endpoint.main.name}/variant/${var.variant_name}"
  scalable_dimension = "sagemaker:variant:DesiredInstanceCount"
  service_namespace  = "sagemaker"

  depends_on = [aws_sagemaker_endpoint.main]
}

# ============================================================================
# Target Tracking Scaling Policy - Invocations Per Instance
# ============================================================================

resource "aws_appautoscaling_policy" "sagemaker_endpoint_invocations" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.project_name}-${var.environment}-endpoint-invocations-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.sagemaker_endpoint[0].resource_id
  scalable_dimension = aws_appautoscaling_target.sagemaker_endpoint[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.sagemaker_endpoint[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = var.target_invocations_per_instance

    predefined_metric_specification {
      predefined_metric_type = "SageMakerVariantInvocationsPerInstance"
    }

    scale_in_cooldown  = 300 # 5 minutes
    scale_out_cooldown = 60  # 1 minute
  }
}

# ============================================================================
# Optional: Scheduled Scaling (example: scale down at night)
# ============================================================================

# Scale down na 1 instanciu v noci (00:00 UTC)
resource "aws_appautoscaling_scheduled_action" "scale_down_night" {
  count = var.enable_autoscaling && var.environment == "prod" ? 0 : 0 # Disabled by default

  name               = "${var.project_name}-${var.environment}-scale-down-night"
  service_namespace  = aws_appautoscaling_target.sagemaker_endpoint[0].service_namespace
  resource_id        = aws_appautoscaling_target.sagemaker_endpoint[0].resource_id
  scalable_dimension = aws_appautoscaling_target.sagemaker_endpoint[0].scalable_dimension
  schedule           = "cron(0 0 * * ? *)" # 00:00 UTC daily

  scalable_target_action {
    min_capacity = 1
    max_capacity = 1
  }
}

# Scale up späť ráno (06:00 UTC)
resource "aws_appautoscaling_scheduled_action" "scale_up_morning" {
  count = var.enable_autoscaling && var.environment == "prod" ? 0 : 0 # Disabled by default

  name               = "${var.project_name}-${var.environment}-scale-up-morning"
  service_namespace  = aws_appautoscaling_target.sagemaker_endpoint[0].service_namespace
  resource_id        = aws_appautoscaling_target.sagemaker_endpoint[0].resource_id
  scalable_dimension = aws_appautoscaling_target.sagemaker_endpoint[0].scalable_dimension
  schedule           = "cron(0 6 * * ? *)" # 06:00 UTC daily

  scalable_target_action {
    min_capacity = var.min_instance_count
    max_capacity = var.max_instance_count
  }
}
