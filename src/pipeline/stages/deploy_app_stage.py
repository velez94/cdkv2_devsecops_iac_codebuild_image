from constructs import Construct
from aws_cdk import (
    Stage,
    # Import Aspects
    Aspects
)
# Add AWS Checks
from cdk_nag import AwsSolutionsChecks, NagSuppressions

from ...stacks.ecr import ECRStack


class PipelineStageDeployApp(Stage):

    def __init__(self, scope: Construct, id: str, props: dict = None, **kwargs):
        super().__init__(scope, id, **kwargs)
        project_name = props.get("repository_name", "").replace("_","-")
        self.stack = ECRStack(
            self,
            f"ECR-{project_name}",
            props=props,
            stack_name= f"ECR-{project_name}"

        )
        # Add aspects
        Aspects.of(self.stack).add(AwsSolutionsChecks(verbose=True))
        # Add Suppression
        NagSuppressions.add_stack_suppressions(stack=self.stack, suppressions=[
            {"id": "AwsSolutions-ECR1", "reason": "Its Necessary for this case"}
        ])
        # set_tags(stack, tags=props["tags"])