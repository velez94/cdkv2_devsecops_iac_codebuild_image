import os

from aws_cdk import Environment

from .helper import load_yamls, load_yamls_to_dict

# Load environment definitions
dirname = os.path.dirname(__file__)

props_paths = "./environment_options/environment_options.yml"

props = (load_yamls(os.path.join(dirname, props_paths)))[0]
env_client_devsecops_account = Environment(account=props['account_devsecops'], region=props['region_devsecops'])
# Load Environments
environments = {}
props["def_environments"] = {}
for e in props["environments"]:

    environments[e["environment"]] = Environment(account=e['deployment_account'], region=e['deployment_region'])
    props["def_environments"][e["environment"]] = e["environment"]
    if "partner_review_email" in e.keys():
        props["def_environments"][e["environment"]] = {"partner_review_email": e["partner_review_email"],
                                                       "deployment_region": e["deployment_region"],
                                                       "deployment_account": e["deployment_account"]}

props["environments"] = environments

# load tags
tags = props['tags']

# Load build spec for apps
path = props["ecr_repository_properties"][0]["app_properties"]["build_spec_path"]
app_build_spec = load_yamls(os.path.join(dirname, path))[0]
props["ecr_repository_properties"][0]["app_properties"]["build_spec"] = app_build_spec
