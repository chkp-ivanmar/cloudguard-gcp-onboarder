variable "gcp_project" {
    type = string
}

variable "gcp_region" {
    type = string
    default = "us-central1"

}

variable "gcp_zone" {
    type = string
    default = "us-central1-a"
}

variable "bucket_name" {
    type = string
    default = "onboarder-bucket"
}

variable function_source_path {
    type = string
    description = "Path to zip file which contains code"
    default = "../cloud-function.zip"
}

variable function_name {
    type = string
    description = "Name of the Cloud Function"
    default = "cloudguard-onboarder"
}

variable CHKP_CLOUDGUARD_ID {
    type = string
    description = "CloudGuard token ID"
}

variable CHKP_CLOUDGUARD_SECRET {
    type = string
    description = "CloudGuard token secret"
}

variable svc_account_name {
    type = string
    description = "Name for the service account that will be created in the new GCP project and will be used to connect to CloudGuard CSPM"
    default = "cgcspm-svc-acc"
}

variable svc_account_display_name {
    type = string
    description = "Display name for the service account"
    default = "CloudGuard service account"
}

variable cloudguard_unit_target {
    type = string
    description = "Unit target in CloudGuard to onboard the GCP project"
    default = ""
}

variable billing_account_id {
    type = string
    description = "Billing account ID to associate the new GCP project(required in order enable APIs)"
}

variable log_level {
    type = string
    description = "Log level for the cloud function"
    default = "DEBUG"
}

variable topic_name {
    type = string
    description = "Pub/Sub topic name"
    default = "projectCreationTopic"
}

variable sink_name {
    type = string
    description = "Organization sink_name"
    default = "newProjectsSink"
}

variable organization_id {
    type = string
    description = "GCP Organization ID"
}