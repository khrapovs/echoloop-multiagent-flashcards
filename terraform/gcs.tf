resource "google_storage_bucket" "sqlite_store" {
  name          = "echoloop-sqlite-store-500808"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}
