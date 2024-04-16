from aws_cdk import (
    aws_chatbot as chatbot,
    aws_sns as sns,
    aws_iam as iam,
    aws_lambda as lambda_,
    Duration,
    RemovalPolicy,
    aws_logs as logs,
    aws_codedeploy as codedeploy,
    CfnOutput,
    aws_codepipeline as codepipeline
)
import os

from constructs import Construct
from .iam_chatbot import IAMAWSChatbot
from cdk_nag import NagSuppressions


class SlackChannelConfiguration(Construct):

    def __init__(self, scope: Construct, construct_id: str,

                 project_name: str,
                 props: dict = None,
                 manual_approval_props: dict = None,
                 pipeline: codepipeline.IPipeline = None,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Iam Role
        chat_iam = IAMAWSChatbot(self, "IAMRole", project_name=project_name)
        dirname = os.path.dirname(__file__)
        manual_approval_enabled = manual_approval_props.get("enabled", False)
        manual_approval_pipeline_name = manual_approval_props.get("manual_approval_pipeline_name")
        manual_approval_stage_name = manual_approval_props.get("manual_approval_stage_name")
        manual_approval_action_name = manual_approval_props.get("manual_approval_action_name")

        # Create sns topic
        self.sns_topíc = sns.Topic(self, project_name, display_name=f"ChatOps{project_name}",
                                   topic_name=f"ChatOps{project_name}")
        # Define properties
        self.slack_conf = (chatbot.SlackChannelConfiguration(self,
                                                             f"SlackChannel-{project_name}",
                                                             slack_channel_configuration_name=f"SlackChatbot-{project_name}",
                                                             role=chat_iam.chat_role,
                                                             # "slackWorkspaceId",
                                                             slack_workspace_id=props["slack_workspace_id"],
                                                             # "slackChannelId"
                                                             slack_channel_id=props["slack_channel_id"],
                                                             # the properties below are optional
                                                             guardrail_policies=[
                                                                 iam.ManagedPolicy.from_aws_managed_policy_name(
                                                                     managed_policy_name="AWSCodePipeline_FullAccess"),
                                                                 iam.ManagedPolicy.from_aws_managed_policy_name(
                                                                     managed_policy_name="ReadOnlyAccess"),
                                                                 iam.ManagedPolicy.from_aws_managed_policy_name(
                                                                     managed_policy_name="AWSLambda_FullAccess")
                                                             ],

                                                             logging_level=chatbot.LoggingLevel.INFO,

                                                             notification_topics=[self.sns_topíc],

                                                             ))

        if manual_approval_enabled:
            # create custom log group for lambda function
            log_group = logs.LogGroup(self, "MannualApprovalLogGroup",
                                      log_group_name=f"/aws/lambda/MannualApprovalLambdaFunction-{project_name}",
                                      removal_policy=RemovalPolicy.DESTROY,
                                      retention=logs.RetentionDays.TWO_WEEKS,

                                      )
            # create lambda for manual approval based on local function code
            lambda_function = lambda_.Function(self, "MannualApprovalLambdaFunction",
                                               function_name=f"MannualApprovalLambdaFunction-{project_name}",
                                               timeout=Duration.seconds(300),
                                               runtime=lambda_.Runtime.PYTHON_3_9,
                                               handler="app.lambda_handler",
                                               code=lambda_.Code.from_asset(
                                                   os.path.join(dirname, "manual_approval/function")),
                                               environment={
                                                   "PIPELINE_NAME" : manual_approval_pipeline_name,
                                                   "STAGE_NAME": manual_approval_stage_name,
                                                   "ACTION_NAME": manual_approval_action_name
                                               },
                                               log_group=log_group,

                                               )

            alias = lambda_.Alias(self, f"{project_name}-LambdaAlias",
                                  alias_name="Prod_2", version=lambda_function.current_version)

            deployment_group = codedeploy.LambdaDeploymentGroup(self, f"{project_name}-lambda-DeploymentGroup",
                                             alias=alias,
                                             deployment_config=codedeploy.LambdaDeploymentConfig.ALL_AT_ONCE
                                             )

            lambda_function.role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodePipelineApproverAccess"))
            # Subscribe notification from pipeline
            pipeline.notify_on_any_manual_approval_state_change(id="ManualApproval",
                                                                         notification_rule_name=f"ManualApprovalNotification{project_name}",
                                                                         target=self.slack_conf
                                                                         )
            # define supressions
            NagSuppressions.add_resource_suppressions([lambda_function, deployment_group],
                                                      suppressions=[
                                                          {"id": "AwsSolutions-IAM4",
                                                           "reason": "CDK Pipelines Construct manage the policy"},
                                                          {"id": "AwsSolutions-IAM5",
                                                           "reason": "CDK Pipelines Construct manage the policy"},
                                                          {"id": "AwsSolutions-L1", "reason": "Intrinsic Property"},

                                                      ],
                                                      apply_to_children=True
                                                      )

        CfnOutput(self, "ConfigurationArn", value=self.slack_conf.slack_channel_configuration_arn)

        # Add Nag Suppression
        NagSuppressions.add_resource_suppressions(self.sns_topíc,
                                                  suppressions=[
                                                      {"id": "AwsSolutions-SNS3",
                                                       "reason": "CDK Pipelines Construct manage the policy"},
                                                      {"id": "AwsSolutions-SNS2", "reason": "Intrinsic Property"},

                                                  ],
                                                  apply_to_children=True
                                                  )
