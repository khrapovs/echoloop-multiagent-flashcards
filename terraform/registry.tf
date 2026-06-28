resource "google_artifact_registry_repository" "echoloop_repo" {
  location      = var.region
  repository_id = "echoloop-repo"
  description   = "Docker repository for EchoLoop container images"
  format        = "DOCKER"

  depends_on = [google_project_service.apis]
}
