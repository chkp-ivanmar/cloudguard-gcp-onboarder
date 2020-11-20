# cloudguard-gcp-onboarder
> Disclaimer: Documentation and reworks in progress
Automatic onboarder for new GCP projects into CloudGuard

## Deploy cloud function using gcloud

```bash
gcloud functions deploy <func-name> \
    --trigger-topic=<topic-name> \
    --region=<region-name> \
    --entry-point=pubsub_process \
    --runtime=python38 \
    --env-vars-file cloud-function/env.vars.yaml \
    --timeout 540 --source cloud-function
```

## Deploy sink using gcloud

```bash
export SINK_NAME=mysink
export PROJECT_ID="my-project-123456"
export TOPIC_NAME="createdProjectsTopic"
export ORGANIZATION_ID="11111111"
gcloud logging sinks create ${SINK_NAME} \
    pubsub.googleapis.com/projects/${PROJECT_ID}/topics/${TOPIC_NAME} \
    --include-children \
    --organization=${ORGANIZATION_ID} \
    --log-filter="resource.type=\"project\" AND protoPayload.methodName=\"CreateProject\""
```
