#!/usr/bin/env python3
import os

import aws_cdk as cdk
# Add AWS Checks
from cdk_nag import AwsSolutionsChecks, NagSuppressions
from aws_cdk import Aspects

from src.pipeline.cdkv2_pipeline_ecr_multiaccount import CdkPipelineECRStack
from project_configs.project_configs import props, environments, env_client_devsecops_account
from project_configs.helper import set_tags

app = cdk.App()
pipeline_stack = CdkPipelineECRStack(app, "Cdkv2DevsecopsIacCodebuildImageStack",
                                     stack_name="Cdkv2DevsecopsIacCodebuildImageStack",
                                     props= props,
                                     dev_env= environments.get("dev"),
                                     env=env_client_devsecops_account

                                     )
set_tags(pipeline_stack, tags=props["tags"])
# Add aspects
Aspects.of(pipeline_stack).add(AwsSolutionsChecks(verbose=True))

app.synth()
