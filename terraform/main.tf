provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
  zone    = var.gcp_zone
}

resource "google_storage_bucket" "function_bucket" {
  name = var.bucket_name
}

resource "google_storage_bucket_object" "archive" {
  name   = "index.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = var.function_source_path
}

resource "google_cloudfunctions_function" "function" {
  name        = var.function_name
  description = "CloudGuard onboarder function"
  runtime     = "python38"

  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.archive.name
  timeout               = 540
  entry_point           = "pubsub_process"
  event_trigger {
      event_type = "google.pubsub.topic.publish"
      resource = google_pubsub_topic.project_topic.name
  }
  environment_variables = {
      GOOGLE_APPLICATION_CREDENTIALS = "credentials/credentials.json"
      CHKP_CLOUDGUARD_ID = var.CHKP_CLOUDGUARD_ID
      CHKP_CLOUDGUARD_SECRET = var.CHKP_CLOUDGUARD_SECRET
      SVC_ACC_NAME = var.svc_account_name
      SVC_ACC_DISPLAY_NAME = var.svc_account_display_name
      ORG_UNIT_TARGET = var.cloudguard_unit_target
      BILLING_ACCOUNT_ID = var.billing_account_id
      LOG_LEVEL = var.log_level

  }
}

resource "google_pubsub_topic" "project_topic" {
  name = var.topic_name
}

# IAM entry for all users to invoke the function
resource "google_cloudfunctions_function_iam_member" "invoker" {
  project        = google_cloudfunctions_function.function.project
  region         = google_cloudfunctions_function.function.region
  cloud_function = google_cloudfunctions_function.function.name

  role   = "roles/cloudfunctions.invoker"
  member = "allAuthenticatedUsers"
}

resource "google_logging_organization_sink" "created_project_sink" {
  name   = var.sink_name
  org_id = var.organization_id

  # Export to pubsub
  destination = "pubsub.googleapis.com/${google_pubsub_topic.project_topic.id}"

  # Log all WARN or higher severity messages relating to instances
  filter = "resource.type = \"project\" AND protoPayload.methodName= \"CreateProject\""
  # Need to include children since the log entry is generated on a project basis
  include_children = true
}

resource "google_pubsub_topic_iam_binding" "binding" {
  project = google_pubsub_topic.project_topic.project
  topic = google_pubsub_topic.project_topic.name
  role = "roles/editor"
  members = [
    google_logging_organization_sink.created_project_sink.writer_identity
  ]
}