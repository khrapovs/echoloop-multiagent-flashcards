output "service_url" {
  value       = google_cloud_run_v2_service.echoloop_ui.uri
  description = "The URL of the deployed EchoLoop Streamlit UI"
}
