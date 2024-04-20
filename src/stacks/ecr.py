from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_ram as ram,
    CfnOutput,
    RemovalPolicy,
    aws_ssm as ssm,
    CfnTag
)
from constructs import Construct


class ECRStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, props: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # Get values

        repo_name = props.get("repository_name", "Repo")
        lifecycle_rule = props.get("lifecycle_rule", {})
        accounts = props.get("resource_policy", []).get("accounts", [])
        ous = props.get("resource_policy", []).get("ous", None)
        projects = props.get("resource_policy", []).get("projects", None)

        self.repository = ecr.Repository(self, f"ECR-{repo_name}",
                                         image_scan_on_push=True,
                                         image_tag_mutability=ecr.TagMutability.IMMUTABLE,
                                         repository_name=repo_name,
                                         encryption=ecr.RepositoryEncryption.KMS,
                                         removal_policy=RemovalPolicy.DESTROY
                                         )
        self.repository.add_lifecycle_rule(
            tag_prefix_list=lifecycle_rule.get("tags_prefix", ["prod"]),
            max_image_count=lifecycle_rule.get("max_images", 15),

            rule_priority=1)
        # Create shared and private parameter store
        shared_p = ssm.StringParameter(self, "PublicParameter",
                                       parameter_name="/devsecopsiac/image/version",
                                       tier=ssm.ParameterTier.ADVANCED,
                                       string_value=props["app_properties"][
                                           "version"],
                                       description="Version for codebuild base image")
        # self.repository.add_lifecycle_rule(
        #    max_image_age=Duration.days(14),
        #    rule_priority=2
        # )
        # Add Resource Policy

        read_actions = [
            "ecr:BatchGetImage",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchCheckLayerAvailability",
            "ecr:DescribeImages",
            "ecr:DescribeRepositories"
        ]
        write_actions = [
            "ecr:BatchGetImage",
            "ecr:BatchCheckLayerAvailability",
            "ecr:CompleteLayerUpload",
            "ecr:GetDownloadUrlForLayer",
            "ecr:InitiateLayerUpload",
            "ecr:PutImage",
            "ecr:UploadLayerPart"
        ]
        actions = {"read": read_actions, "write": write_actions}

        if projects is not None and len(projects) > 0:
            for p in projects:
                act = p.get("type", "read")

                st_p = iam.PolicyStatement(actions=actions.get(act),
                                           effect=iam.Effect.ALLOW,
                                           principals=[iam.ServicePrincipal(service="codebuild.amazonaws.com")],
                                           conditions={
                                               "ArnLike": {
                                                   "aws:SourceArn": f"arn:aws:codebuild:{p.get('region', 'us-east-1')}:{p.get('account', '*')}:project/{p.get('name', '*')}*"
                                               },
                                               "StringEquals": {
                                                   "aws:SourceAccount": f"{p.get('account', '*')}"
                                               }
                                           },

                                           )
                self.repository.add_to_resource_policy(statement=st_p)

        if accounts is not None and len(accounts) > 0:
            principals =[]
            for a in accounts:
                act = a.get("type", "read")

                st_ac = iam.PolicyStatement(actions=actions.get(act),
                                            effect=iam.Effect.ALLOW,
                                            principals=[iam.AccountPrincipal(account_id=a.get("account_id"))],

                                            )



                principals.append(a.get("account_id"))
                self.repository.add_to_resource_policy(statement=st_ac)
            # Create share resource invitation for other accounts
            shared_ram = ram.CfnResourceShare(self, "ACSharedDevSecOpsIaCParam",
                                                      name="ACSharedDevSecOpsIaCParam",

                                                      # the properties below are optional
                                                      allow_external_principals=True,

                                                      principals=principals,
                                                      resource_arns=[shared_p.parameter_arn],

                                                      )
            CfnOutput(self, "SharedARN", value=shared_ram.attr_arn, description="RAM Parameter Store ARN")
        if ous is not None and len(ous) > 0:
            principals_ou= []
            for o in ous:
                act = o.get("type", "read")

                st_ou = iam.PolicyStatement(actions=actions.get(act),
                                            effect=iam.Effect.ALLOW,
                                            principals=[iam.AnyPrincipal()],

                                            conditions={

                                                "ForAnyValue:StringLike": {

                                                    "aws:PrincipalOrgPaths": o["id"]

                                                }

                                            }
                                            )

                self.repository.add_to_resource_policy(statement=st_ou)

            # Define Outputs
        CfnOutput(self, "RepoARN", value=self.repository.repository_arn, description="Repository ARN")
        CfnOutput(self, "RepoURI", value=self.repository.repository_uri, description="Repository URI")
