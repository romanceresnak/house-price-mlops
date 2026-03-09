# ============================================================================
# ECS Cluster
# ============================================================================

resource "aws_ecs_cluster" "mlflow" {
  name = "${var.project_name}-${var.environment}-mlflow-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-mlflow-cluster"
  }
}

# ============================================================================
# CloudWatch Log Group pre ECS tasks
# ============================================================================

resource "aws_cloudwatch_log_group" "mlflow" {
  name              = "/ecs/${var.project_name}-${var.environment}-mlflow"
  retention_in_days = 30

  tags = {
    Name = "${var.project_name}-${var.environment}-mlflow-logs"
  }
}

# ============================================================================
# ECS Task Definition
# ============================================================================

resource "aws_ecs_task_definition" "mlflow" {
  family                   = "${var.project_name}-${var.environment}-mlflow"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.mlflow_cpu
  memory                   = var.mlflow_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "mlflow"
      image     = var.mlflow_image
      essential = true

      portMappings = [
        {
          containerPort = var.mlflow_port
          protocol      = "tcp"
        }
      ]

      # MLflow command
      command = [
        "mlflow",
        "server",
        "--backend-store-uri",
        "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.mlflow.address}:${aws_db_instance.mlflow.port}/${var.db_name}",
        "--default-artifact-root",
        "s3://${aws_s3_bucket.mlflow_artifacts.id}/artifacts",
        "--host",
        "0.0.0.0",
        "--port",
        tostring(var.mlflow_port)
      ]

      # Environment variables
      environment = [
        {
          name  = "AWS_DEFAULT_REGION"
          value = var.aws_region
        },
        {
          name  = "MLFLOW_S3_ENDPOINT_URL"
          value = "https://s3.${var.aws_region}.amazonaws.com"
        }
      ]

      # Secrets (DB credentials z Secrets Manager)
      secrets = [
        {
          name      = "DB_USERNAME"
          valueFrom = "${aws_secretsmanager_secret.mlflow_db.arn}:username::"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.mlflow_db.arn}:password::"
        }
      ]

      # Logging
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.mlflow.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "mlflow"
        }
      }

      # Health check
      healthCheck = {
        command = [
          "CMD-SHELL",
          "curl -f http://localhost:${var.mlflow_port}/health || exit 1"
        ]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-${var.environment}-mlflow-task"
  }
}

# ============================================================================
# ECS Service
# ============================================================================

resource "aws_ecs_service" "mlflow" {
  name            = "${var.project_name}-${var.environment}-mlflow-service"
  cluster         = aws_ecs_cluster.mlflow.id
  task_definition = aws_ecs_task_definition.mlflow.arn
  desired_count   = var.mlflow_desired_count
  launch_type     = "FARGATE"

  # Network configuration
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  # Load balancer integration
  load_balancer {
    target_group_arn = aws_lb_target_group.mlflow.arn
    container_name   = "mlflow"
    container_port   = var.mlflow_port
  }

  # Deployment configuration
  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  # Auto-scaling (optional)
  enable_execute_command = true

  # Wait for ALB to be ready
  depends_on = [
    aws_lb_listener.http,
    aws_iam_role_policy.ecs_task_s3
  ]

  tags = {
    Name = "${var.project_name}-${var.environment}-mlflow-service"
  }
}

# ============================================================================
# Auto Scaling Target
# ============================================================================

resource "aws_appautoscaling_target" "mlflow" {
  max_capacity       = 4
  min_capacity       = var.mlflow_desired_count
  resource_id        = "service/${aws_ecs_cluster.mlflow.name}/${aws_ecs_service.mlflow.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU utilization
resource "aws_appautoscaling_policy" "mlflow_cpu" {
  name               = "${var.project_name}-${var.environment}-mlflow-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.mlflow.resource_id
  scalable_dimension = aws_appautoscaling_target.mlflow.scalable_dimension
  service_namespace  = aws_appautoscaling_target.mlflow.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# Auto Scaling Policy - Memory utilization
resource "aws_appautoscaling_policy" "mlflow_memory" {
  name               = "${var.project_name}-${var.environment}-mlflow-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.mlflow.resource_id
  scalable_dimension = aws_appautoscaling_target.mlflow.scalable_dimension
  service_namespace  = aws_appautoscaling_target.mlflow.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = 80.0
  }
}
