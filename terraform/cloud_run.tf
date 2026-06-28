# Create a dedicated Service Account for the Cloud Run service
resource "google_service_account" "cloud_run_sa" {
  account_id   = "echoloop-run-sa"
  display_name = "Service Account for EchoLoop Cloud Run service"
}

# Grant the Service Account Vertex AI User access to call Gemini models
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Grant the Service Account read/write access to the SQLite bucket
resource "google_storage_bucket_iam_member" "bucket_admin" {
  bucket = google_storage_bucket.sqlite_store.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Deploy the Cloud Run Service
resource "google_cloud_run_v2_service" "echoloop_ui" {
  name     = "echoloop-ui"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run_sa.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.echoloop_repo.repository_id}/echoloop:${var.image_tag}"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          memory = "1Gi"
          cpu    = "1000m"
        }
      }

      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "True"
      }

      env {
        name  = "ECHOLOOP_DB_DIR"
        value = "/data"
      }

      env {
        name  = "ALLOWED_IPS"
        value = var.allowed_ips
      }

      volume_mounts {
        name       = "sqlite-volume"
        mount_path = "/data"
      }
    }

    volumes {
      name = "sqlite-volume"
      gcs {
        bucket    = google_storage_bucket.sqlite_store.name
        read_only = false
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.apis,
    google_project_iam_member.vertex_ai_user,
    google_storage_bucket_iam_member.bucket_admin
  ]
}

# Allow public (unauthenticated) traffic to the service (IP whitelist is enforced in app)
resource "google_cloud_run_v2_service_iam_member" "allow_public" {
  location = google_cloud_run_v2_service.echoloop_ui.location
  project  = google_cloud_run_v2_service.echoloop_ui.project
  name     = google_cloud_run_v2_service.echoloop_ui.name
  role     = "roles/run.viewer"
  member   = "allUsers"
}
