from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from  googleapiclient import discovery
import logging
import os
import json
import time

formatter = logging.Formatter('{asctime}:{name}:{message}', style='{')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(stream_handler)

level = logging.getLevelName(os.environ.get('LOG_LEVEL', 'INFO'))
logger.setLevel(level)

APIS_TO_ENABLE = {
    'serviceIds': [
        'cloudbilling',
        'compute',
        'cloudresourcemanager',
        'container',
        'cloudkms',
        'iam',
        'bigquery',
        'admin',
        'cloudfunctions',
        'sqladmin',
        'bigtableadmin',
        'pubsub',
        'redis'
    ]
}

ROLES_TO_ADD = [
    'roles/iam.securityReviewer',
    'roles/viewer'
]

# TODO: Get billing account id from environment variables
# TODO: Document hwo to get the billing account ID to use

class GCPClient(object):
    def __init__(self, project):
        self.project = project
        self.project_id = project.split('/', 1)[-1]
        self.billing_account_id = os.getenv('BILLING_ACCOUNT_ID', None)
        if self.billing_account_id is None:
            raise Exception("Need to define BILLING_ACCOUNT_ID environment variable")
        self.cloudbilling = discovery.build('cloudbilling', 'v1')
        self.serviceusage = discovery.build('serviceusage', 'v1')
        self.iam = discovery.build('iam', 'v1')
        self.cloudresourcemanager = discovery.build('cloudresourcemanager', 'v1')

    def update_project_billing(self):
        self.enable_apis(['cloudbilling'])
        billing_info = self.get_project_billing_info()

        # Check if the project created already has billing information.
        # If not, it has to be set in order to enable APIs
        if not billing_info['billingAccountName'] and billing_info['billingEnabled'] is False:
           billing_info['billingAccountName'] = self.billing_account_id
           billing_info['billingEnabled'] = True   
        else:
            return
        try:
            logger.debug(f"Billing info to apply:\n{json.dumps(billing_info, indent=2)}")
            response = self.cloudbilling.projects().updateBillingInfo(name=self.project, body=billing_info).execute()
            logger.debug(f"Updated billing info: {response}")
        except Exception as e:
            logger.error(f"Exception during the update of billing information for project: {self.project}")
            logger.error(e)
            raise

    def get_project_billing_info(self):
        try:
            response = self.cloudbilling.projects().getBillingInfo(name=self.project).execute()
            logger.debug(f"Project billing info:{json.dumps(response, indent=2)}")
            return response
        except Exception as e:
            logger.error(f"Error trying to get billing info for project: {self.project}")
            logger.error(e)
            return None

    def get_api_info(self, api_name):
        try:
            response = self.serviceusage.services().get(name=f"{self.project}/services/{api_name}.googleapis.com").execute()
            name = response.get('config').get('name')
            state = response.get('state')
            logger.info(f"{name}  {state}")
            return state
        except Exception as e:
            logger.error(e) 
            raise
        
    def enable_apis(self, apis=APIS_TO_ENABLE['serviceIds']):
        for api in apis:
            state = self.get_api_info(api)
            if state.lower() == 'enabled':
                logger.warn(f"API {api} already enabled. Skip to next")
                continue
            response = ''
            try:
                response = self.serviceusage.services().enable(name=f"{self.project}/services/{api}.googleapis.com").execute()
            except Exception as e:
                logger.error(e)
                raise
            logger.info(f"Updated result for api {api}: {response}")
            # Wait until API is enabled
            t_end = time.time() + 300 # 5 minute to retry
            while time.time() < t_end:
                state = self.get_api_info(api)
                if state.lower() != 'enabled':
                   logger.debug(f"API {api} state is {state}. Retrying...")
                   time.sleep(30)
                else:
                    break
            if state.lower() != 'enabled':
                logger.error(f"Couldn't enable API {api}")
                raise Exception(f"API {api} couldn't be enabled")

    def list_api_state(self, apis=APIS_TO_ENABLE['serviceIds']):
        for api in apis:
            self.get_api_info(api)

    def generate_project_policy(self, policy, svc_account_email):
        if 'bindings' not in policy:
            policy['bindings'] = []
     
        for role in ROLES_TO_ADD: 
            binding_to_update = None 
            try:
                binding_to_update = next(item for item in policy['bindings'] if item['role'] == role)
            except Exception as e:
                logger.warn(e)
                logger.warn(f"Role: {role} is not present in current policy. Needs creation")
            
            if binding_to_update is not None:
                # Append 
                binding_to_update['members'].append(
                    f"serviceAccount:{svc_account_email}"
                )
            else:
                # Create
                policy['bindings'].append(
                    {
                       "role": role,
                       "members": [
                           f"serviceAccount:{svc_account_email}"
                       ] 
                   }
                )
        return policy 


    def add_svc_acc_to_policy(self, policy, svc_account_email):
        if 'bindings' not in policy:
            policy['bindings'] = []
        
        for role in ROLES_TO_ADD:
            policy['bindings'].append(
                {
                    "role": role,
                    "members": [
                        f"serviceAccount:{svc_account_email}"
                    ]
                }
            )

    def get_iam_policy(self, svc_account):
        try:
            iam_policy = self.discovery.projects().serviceAccounts().getIamPolicy(
                resource=f"{self.project}/serviceAccounts/{svc_account}"
            ).execute()
            logger.debug(f"IAM policy: {json.dumps(iam_policy, indent=2)}")
            return iam_policy
        except Exception as e:
            logger.error(e)
            raise


    def get_svc_acc_iam_policy(self, svc_account_name):
        try:
            iam_policy = self.discovery.projects().serviceAccounts().getIamPolicy(
                resource=svc_account_name
            ).execute()
            logger.debug(f"Current IAM policy: {iam_policy}")
            return iam_policy
        except Exception as e:
            logger.error(e)
            raise

    def set_svc_acc_iam_policy(self, svc_account_name, iam_policy):
        body_payload = {
            'policy': iam_policy
        }
        try:
            updated_policy = self.iam.projects().serviceAccounts().setIamPolicy(
                resource=svc_account_name,
                body=body_payload
            ).execute()
            logger.debug(f"Updated IAM policy: {updated_policy}")
            return updated_policy
        except Exception as e:
            logger.error(e)
            raise

    def get_project_iam_policy(self):
        try:
            iam_policy = self.cloudresourcemanager.projects().getIamPolicy(
                resource=self.project_id
            ).execute()
            logger.debug(f"Project IAM policy:\n{json.dumps(iam_policy, indent=2)}")
            return iam_policy
        except Exception as e:
            logger.error(e)
            raise

    def set_project_iam_policy(self, iam_policy):
        body_payload = {
            'policy': iam_policy
        }
        try:
            iam_policy = self.cloudresourcemanager.projects().setIamPolicy(
                resource=self.project_id,
                body=body_payload
            ).execute()
            logger.debug(f"Update Project IAM policy:\n{json.dumps(iam_policy, indent=2)}")
        except Exception as e:
            logger.error(e)
            raise

    def get_svc_account_by_display_name(self, display_name):
        request = self.iam.projects().serviceAccounts().list(name=self.project)
        svc_account = None
        while True:
            response = request.execute()
            try:
                svc_account = next(acc for acc in response['accounts'] if acc['displayName'] == display_name)
                # Break the loop if we manage to get the svc_account
                if svc_account is not None:
                    break
            except Exception:
                # The account may not be present in this chunk so we need to continue processing
                request = self.iam.projects().serviceAccounts().list_next(previous_request=request, previous_response=response)
                if request is None:
                    logger.error(f"Couldn't find service account by display name: {display_name}")
                    raise 
        return svc_account


    def create_svc_account(self, svc_name='cloudguard-svc-account', display_name=''):
        try:
            service_account = self.iam.projects().serviceAccounts().create(
                name=self.project,
                body={
                    'accountId': svc_name,
                    'serviceAccount': {
                        'displayName': display_name
                    }
                }).execute()
        except HttpError as err:
            if err.resp.status in [409]:
                logger.info(f"Service account {svc_name} already exists. Trying to fetch it")
                return self.get_svc_account_by_display_name(display_name)
            else: 
                logger.error(f"Couldn't get existing service account by display name: {display_name}")
                raise
            
        logger.info(f"New service account info: {service_account}")
        return service_account


    def create_svc_account_key(self, service_account):
        key = self.iam.projects().serviceAccounts().keys().create(
            name=f"{self.project}/serviceAccounts/{service_account['email']}",
            body={
                "privateKeyType": "TYPE_GOOGLE_CREDENTIALS_FILE"
            }).execute()
        logger.info(f"New key info: {key}")
        return key