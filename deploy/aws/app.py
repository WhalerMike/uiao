#!/usr/bin/env python3
"""
UIAO AWS SaaS — CDK app entrypoint (ADR-117).

The AWS analogue of ``deploy/azure/bicep/main.bicep``'s deployment driver.
Configuration comes from CDK context (``-c key=value`` or ``cdk.context.json``)
so the same app synthesizes per-environment stacks:

    cdk synth -c environmentName=dev
    cdk deploy -c environmentName=prod -c imageUri=<acct>.dkr.ecr.<r>.amazonaws.com/uiao-saas:latest

Account/region resolve from the standard ``CDK_DEFAULT_ACCOUNT`` /
``CDK_DEFAULT_REGION`` environment the CDK CLI injects.
"""

from __future__ import annotations

import os

from aws_cdk import App, Environment, Tags
from uiao_saas_stack import UiaoSaasStack

app = App()

environment_name = app.node.try_get_context("environmentName") or "dev"
image_uri = app.node.try_get_context("imageUri") or ""
cloud = app.node.try_get_context("cloud") or "commercial"
app_client_id = app.node.try_get_context("appClientId") or ""
publisher_tenant_id = app.node.try_get_context("publisherTenantId") or ""
api_audience = app.node.try_get_context("apiAudience") or "api://uiao"

env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

stack = UiaoSaasStack(
    app,
    f"uiao-saas-{environment_name}",
    env=env,
    image_uri=image_uri,
    cloud=cloud,
    app_client_id=app_client_id,
    publisher_tenant_id=publisher_tenant_id,
    api_audience=api_audience,
)

Tags.of(stack).add("workload", "uiao")
Tags.of(stack).add("environment", environment_name)
Tags.of(stack).add("component", "uiao-saas")
Tags.of(stack).add("adr", "adr-117")

app.synth()
