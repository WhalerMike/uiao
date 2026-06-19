"""
UIAO Azure-parity SaaS stack on AWS (ADR-117).

The AWS analogue of ``deploy/azure/bicep/main.bicep``: it stamps the shared
multi-tenant SaaS platform — VPC, an RDS PostgreSQL tenant registry, an ECS
Fargate service behind an Application Load Balancer running
``uiao.saas.asgi:app``, an S3 evidence bucket, and the IAM task role that ties
them together.

Hardening mirrors the Azure surface (ADR-116):

* **Passwordless Postgres.** RDS IAM database authentication is enabled and the
  task role is granted ``rds-db:connect`` for the ``uiao_app`` user; the app
  presents a short-lived IAM token as the connection password
  (``uiao.saas.aws_pg_auth``). No long-lived DB password reaches the task.
* **Private data tier.** RDS is in private subnets, not publicly accessible,
  reachable only from the service security group.
* **Encrypted, private storage.** The evidence bucket enforces TLS, blocks
  public access, and is encrypted + versioned.

The ``uiao_app`` database role (with the ``rds_iam`` role granted) is created
as a one-time data-plane step after first deploy — see ``deploy/aws/README.md``.
"""

from __future__ import annotations

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_ecs_patterns as ecs_patterns,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_rds as rds,
)
from aws_cdk import (
    aws_s3 as s3,
)
from constructs import Construct

#: The database role the app authenticates as (must hold the rds_iam role).
DB_APP_USER = "uiao_app"
DB_NAME = "uiao"
CONTAINER_PORT = 8000
#: Placeholder image used at synth when no ECR URI is supplied. Real deploys
#: pass ``-c imageUri=<acct>.dkr.ecr.<region>.amazonaws.com/uiao-saas:<tag>``
#: (built + pushed separately, mirroring the Azure ``az acr build`` flow).
DEFAULT_IMAGE = "uiao-saas:latest"


class UiaoSaasStack(Stack):
    """The shared UIAO SaaS platform on AWS ECS Fargate + RDS."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        image_uri: str = "",
        cloud: str = "commercial",
        app_client_id: str = "",
        publisher_tenant_id: str = "",
        api_audience: str = "api://uiao",
        desired_count: int = 2,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, "Vpc", max_azs=2, nat_gateways=1)

        # --- Tenant registry: RDS PostgreSQL, IAM auth, private -------------
        registry = rds.DatabaseInstance(
            self,
            "Registry",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            iam_authentication=True,
            database_name=DB_NAME,
            credentials=rds.Credentials.from_generated_secret("uiaoadmin"),
            publicly_accessible=False,
            storage_encrypted=True,
            allocated_storage=20,
            backup_retention=Duration.days(7),
            removal_policy=RemovalPolicy.SNAPSHOT,
        )

        # --- Evidence-bundle storage: private, encrypted, versioned --------
        evidence = s3.Bucket(
            self,
            "Evidence",
            enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, container_insights=True)

        # Pre-built ECR image (cloud-neutral uiao-saas, same Dockerfile as the
        # Azure surface). Built + pushed by CI before `cdk deploy`.
        image = ecs.ContainerImage.from_registry(image_uri or DEFAULT_IMAGE)

        # Passwordless DSN — no password; the app mints an RDS IAM token as the
        # connection password at runtime (uiao.saas.aws_pg_auth).
        database_url = f"postgresql+asyncpg://{DB_APP_USER}@{registry.instance_endpoint.hostname}:5432/{DB_NAME}"

        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "Saas",
            cluster=cluster,
            cpu=512,
            memory_limit_mib=1024,
            desired_count=desired_count,
            public_load_balancer=True,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=image,
                container_port=CONTAINER_PORT,
                environment={
                    "PORT": str(CONTAINER_PORT),
                    "UIAO_SAAS_CLOUD": cloud,
                    "UIAO_SAAS_APP_CLIENT_ID": app_client_id,
                    "UIAO_SAAS_PUBLISHER_TENANT_ID": publisher_tenant_id,
                    "UIAO_SAAS_API_AUDIENCE": api_audience,
                    "UIAO_SAAS_PROVISIONING_ENABLED": "true",
                    "UIAO_SAAS_DATABASE_URL": database_url,
                    "UIAO_SAAS_DATABASE_USE_AWS_IAM_AUTH": "true",
                    "UIAO_SAAS_AWS_REGION": self.region,
                    "UIAO_SAAS_AWS_S3_BUCKET": evidence.bucket_name,
                },
            ),
        )

        # Readiness probe target — /readyz confirms the registry is reachable
        # (ADR-115) before the task joins the load-balancer pool.
        service.target_group.configure_health_check(
            path="/readyz",
            healthy_http_codes="200",
            interval=Duration.seconds(15),
        )

        task_role = service.task_definition.task_role

        # Passwordless DB access: rds-db:connect for the uiao_app user, plus a
        # security-group path from the service to the database.
        registry.grant_connect(task_role, DB_APP_USER)
        registry.connections.allow_default_port_from(service.service, "ECS Fargate service")

        # Evidence bucket: per-tenant S3 prefixes.
        evidence.grant_read_write(task_role)

        # Per-tenant Secrets Manager scopes (uiao/<namespace>/...).
        task_role.add_to_principal_policy(
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:CreateSecret",
                    "secretsmanager:DeleteSecret",
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:PutSecretValue",
                ],
                resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:uiao/*"],
            )
        )

        CfnOutput(self, "LoadBalancerDns", value=service.load_balancer.load_balancer_dns_name)
        CfnOutput(self, "RegistryEndpoint", value=registry.instance_endpoint.hostname)
        CfnOutput(self, "EvidenceBucket", value=evidence.bucket_name)
