variable "project_id" {
  type        = string
  description = "The GCP project ID to deploy resources to."
  default     = "echoloop-500808"
}

variable "region" {
  type        = string
  description = "The GCP region to deploy resources in."
  default     = "us-east1"
}

variable "allowed_ips" {
  type        = string
  description = "Comma-separated list of whitelisted client IP addresses."
  default     = ""
}

variable "image_tag" {
  type        = string
  description = "The Docker container image tag to deploy."
  default     = "latest"
}
