import aws_cdk as core
import aws_cdk.assertions as assertions

from ...src.pipeline.cdkv2_pipeline_ecr_multiaccount import CdkPipelineECRStack
from ...project_configs.project_configs import props, environments, env_client_devsecops_account
from ...project_configs.helper import set_tags


def test_pipeline_created():
    app = core.App()
    stack = CdkPipelineECRStack(app, "Cdkv2DevsecopsIacCodebuildImageStack",
                                stack_name="Cdkv2DevsecopsIacCodebuildImageStack",
                                props=props,
                                dev_env=environments.get("dev"),
                                env=env_client_devsecops_account)
    template = assertions.Template.from_stack(stack)
    template.has_resource_properties("AWS::CodePipeline::Pipeline", {
        "Stages": [
            {

                "Name": "Source"
            },
            {

                "Name": "Build"
            },
            {

                "Name": "UpdatePipeline"
            },
            {

                "Name": "DeployApp"
            }
        ]
    }
                                     )
