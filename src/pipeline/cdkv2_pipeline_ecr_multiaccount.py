import os
from aws_cdk import (
    # Duration,
    Stack,
    pipelines,
    aws_codecommit as codecommit,
    Environment,
    CfnOutput,
    aws_codebuild as codebuild,
    RemovalPolicy,
    aws_ssm as ssm

)
from constructs import Construct
from .stages.deploy_app_stage import PipelineStageDeployApp
from cdk_nag import NagSuppressions
from ..lib.aws_chatbot.slack_construct import SlackChannelConfiguration


class CdkPipelineECRStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,
                 dev_env=Environment,
                 stg_env=Environment,
                 props: dict = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        chatops = props.get("chatops", {})
        pipeline_name = f"Pipeline_{props['project_name']}"
        # Create repository

        rep = codecommit.Repository(
            self,
            props["repository_properties"]["repository_name"],
            repository_name=props["repository_properties"]["repository_name"],
            description=props["repository_properties"]["description"],

        )

        # Create pipeline source based on codecommit repository
        source = pipelines.CodePipelineSource.code_commit(
            repository=rep,
            branch=props["repository_properties"]["branch"]
        )

        # Create pipeline
        pipeline = pipelines.CodePipeline(
            self,
            f"Pipeline{props['project_name']}",
            cross_account_keys=True,
            pipeline_name=pipeline_name,
            synth=pipelines.ShellStep("Synth",
                                      input=source,
                                      commands=[
                                          "npm install -g aws-cdk",
                                          "pip install -r requirements.txt",
                                          "npx cdk synth"
                                      ]
                                      ),

            self_mutation=True,

        )
        # Create unit test step
        unit_test_step = pipelines.CodeBuildStep("UnitTests", project_name=f"UnitTests_{props['project_name']}",
                                                 commands=[
                                                     "pip install pytest",
                                                     "pip install -r requirements.txt",
                                                     "python3 -m pytest --junitxml=unit_test.xml"
                                                 ],
                                                 partial_build_spec=codebuild.BuildSpec.from_object(
                                                     {"version": '0.2',
                                                      "reports": {
                                                          f"Pytest-{props['project_name']}-Report": {
                                                              "files": [
                                                                  "unit_test.xml"
                                                              ],

                                                              "file-format": "JUNITXML"

                                                          }
                                                      }
                                                      }
                                                 )
                                                 )
        # Create SAST Step for Infrastructure
        sast_test_step = pipelines.CodeBuildStep("SASTTests", project_name=f"SASTTests_{props['project_name']}",
                                                 commands=[
                                                     "pip install checkov",
                                                     "ls -all",
                                                     "checkov -d . -o junitxml --output-file . --soft-fail"
                                                 ],
                                                 partial_build_spec=codebuild.BuildSpec.from_object(
                                                     {"version": '0.2',
                                                      "reports": {
                                                          f"checkov-{props['project_name']}-Report": {
                                                              "files": [
                                                                  "results_junitxml.xml"
                                                              ],

                                                              "file-format": "JUNITXML"

                                                          }
                                                      }
                                                      }
                                                 ),
                                                 input=pipeline.synth.primary_output

                                                 )
        # Create SAST Step for Infrastructure
        # Load environment definitions

        # Modify properties, bucket name

        # Create stages
        deploy_dev = PipelineStageDeployApp(self, "DeployApp",
                                            props=props["ecr_repository_properties"][0], env=dev_env)

        # Add Stage
        deploy_dev_stg = pipeline.add_stage(deploy_dev)
        # Add Unit test pre step
        deploy_dev_stg.add_pre(unit_test_step)
        # Add SAST step
        deploy_dev_stg.add_pre(sast_test_step)

        # manual approval props for slack
        manual_approval_props = {"enabled": False}
        if props["ecr_repository_properties"][0]["deploy_app"] == "True":
            # Add manual approval to promote staging
            manual_approval_props["enabled"] = True
            manual_approval_stage_name = deploy_dev_stg.stage_name
            manual_approval_action_name = "ApprovePushImage"
            manual_approval = pipelines.ManualApprovalStep(manual_approval_action_name,
                                                           comment="Allow Push New Image version")
            # manual approval props for slack
            manual_approval_props["manual_approval_stage_name"] = manual_approval_stage_name
            manual_approval_props["manual_approval_action_name"] = manual_approval_action_name
            manual_approval_props["manual_approval_pipeline_name"] = pipeline_name

            # Define Dependency
            build_spec = props["ecr_repository_properties"][0]["app_properties"]["build_spec"]
            push_image_step = pipelines.CodeBuildStep("PushImageStep",
                                                      project_name="PushImageStep",
                                                      env={
                                                          "AWS_ACCOUNT_ID": dev_env.account,
                                                          "AWS_DEFAULT_REGION": dev_env.region,
                                                          "IMAGE_REPO_NAME": props["ecr_repository_properties"][0][
                                                              "repository_name"],
                                                          "IMAGE_TAG":
                                                              props["ecr_repository_properties"][0]["app_properties"][
                                                                  "version"]
                                                      },
                                                      commands=[
                                                          "ls -all",

                                                      ],
                                                      build_environment=codebuild.BuildEnvironment(
                                                          privileged=True,
                                                          build_image=codebuild.LinuxBuildImage.STANDARD_6_0
                                                      ),
                                                      partial_build_spec=codebuild.BuildSpec.from_object(build_spec),

                                                      input=source

                                                      )
            push_image_step.add_step_dependency(manual_approval)

            deploy_dev_stg.add_post(manual_approval, push_image_step)

            # Create public and private parameter store
            ssm.StringParameter(self, "PublicParameter", parameter_name="/devsecopsiac/image/version",
                                string_value=props["ecr_repository_properties"][0]["app_properties"][
                                    "version"],
                                description="Version for codebuild base image")

        # Build Pipeline
        pipeline.build_pipeline()
        pipeline.pipeline.artifact_bucket.apply_removal_policy(RemovalPolicy.DESTROY)

        if chatops["slack_integration"]["enable"] == "true":
            SlackChannelConfiguration(self, "SlackChannel", props=chatops["slack_integration"],
                                              project_name=props["project_name"],
                                              manual_approval_props=manual_approval_props,
                                              pipeline=pipeline.pipeline)


        # Extend permissions role push image step after build pipeline
        if props["ecr_repository_properties"][0]["deploy_app"] == "True":
            deploy_dev.stack.repository.grant_pull_push(push_image_step)

        # Define Outputs
        CfnOutput(self, "GRCRepoUrl", value=rep.repository_clone_url_grc, description="GRC Repository Url")
        CfnOutput(self, "PipelineArn", value=pipeline.pipeline.pipeline_arn, description="Pipeline ARN")
        CfnOutput(self, "StageDev", value=deploy_dev.stage_name, description="Stage Dev Name")

        # Add Nag Suppression
        NagSuppressions.add_resource_suppressions(pipeline,
                                                  suppressions=[
                                                      {"id": "AwsSolutions-IAM5",
                                                       "reason": "CDK Pipelines Construct manage the policy"},
                                                      {"id": "AwsSolutions-CB4", "reason": "Intrinsic Property"},
                                                      {"id": "AwsSolutions-S1",
                                                       "reason": "Intrinsic Property, Bucket logging is necessary"},
                                                      {"id": "AwsSolutions-KMS5",
                                                       "reason": "Intrinsic Property, KMS is manage by CDK Pipeline Construct"},
                                                  ],
                                                  apply_to_children=True
                                                  )
