import json
import os
import time
import base64
from cloudguard import CloudGuardAPI
from gcp import GCPClient
import logging
from utils import decode_key

formatter = logging.Formatter('{asctime}:{name}:{message}', style='{')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(stream_handler)

level = logging.getLevelName(os.environ.get('LOG_LEVEL', 'INFO'))
logger.setLevel(level)

def pubsub_process(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    pubsub_message = json.loads(base64.b64decode(event['data']).decode('utf-8'))

    project =  pubsub_message['protoPayload']['resourceName']
    project_name = pubsub_message['protoPayload']['request']['project']['name']

    logger.info(f"New project created: {project}. Starting onboarding process into CloudGuard")
    gcp_client = GCPClient(project)

    gcp_client.update_project_billing()
    gcp_client.enable_apis()

    svc_name = os.getenv('SVC_ACC_NAME', 'cloudguard-svc-account')
    display_name = os.getenv('SVC_ACC_DISPLAY_NAME', 'CloudGuard svc account')
    org_unit_target = os.getenv('ORG_UNIT_TARGET', '')

    svc_account = gcp_client.create_svc_account(svc_name=svc_name, display_name=display_name)
    iam_policy = gcp_client.get_project_iam_policy()
    policy = gcp_client.generate_project_policy(iam_policy, svc_account['email'])
    gcp_client.set_project_iam_policy(policy)
    logger.debug(f"Updated policy:\n{json.dumps(policy, indent=2)}")
    key = gcp_client.create_svc_account_key(svc_account)
    key_json = decode_key(key['privateKeyData'])

    org_id = get_org_unit_id(org_unit_target)
    onboard_gcp_account(project_name, key_json, org_id)
    
def get_org_unit_id(org_unit_target):
    client = CloudGuardAPI()
    org_units = client.get('organizationalunit/GetFlatOrganizationalUnits')
    logger.debug(f"flat org_units:\n{json.dumps(org_units, indent=2)}")
    
    # Return empty String since we don't have any specific organizational unit
    if len(org_units) == 0:
        return ''
    try:
        org = next(unit for unit in org_units if unit['name'].strip() == org_unit_target.strip())
        return org['id'] 
    except Exception:
        logger.warn(f"The organizational unit does not exist. Will onboard on the root organization")
        return ''

def onboard_gcp_account(name, key, org_id):
    client = CloudGuardAPI() 
    payload = {
        'name': name,
        'serviceAccountCredentials': key,
        'organizationalUnitId': org_id
    }
    gcp_account = client.post('GoogleCloudAccount', payload=json.dumps(payload, indent=2))
    logger.debug(f"Organization onboard result:\n{json.dumps(gcp_account, indent=2)}")
