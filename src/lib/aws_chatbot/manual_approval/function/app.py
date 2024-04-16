import os
import boto3


def lambda_handler(event, context):
    pipeline_name = os.environ['PIPELINE_NAME']
    stage_name = os.environ['STAGE_NAME']
    action = os.environ['ACTION_NAME']
    summary = event['summary']
    status = event['status']

    # print event parameters and environment vars
    print(f"According to {event} and os environment vars {pipeline_name} - {stage_name}")

    client = boto3.client('codepipeline')

    get_token = client.get_pipeline_state(
        name=pipeline_name

    )

    states = get_token['stageStates']
    token= ""
    for s in states:
        if s['stageName'] == stage_name:
            action_states = s['actionStates']
            for a in action_states:
                if a['actionName'] == action:
                    token = a['latestExecution']['token']
                    break
    #['actionStates']['latestExecution']['token']

    response = client.put_approval_result(
        pipelineName=pipeline_name,
        stageName=stage_name,
        actionName=action,
        result={
            'summary': summary,
            'status': status
        },
        token=token

    )
    print(response)
