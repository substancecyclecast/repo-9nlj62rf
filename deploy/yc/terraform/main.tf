terraform {
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.124"
    }
  }
}

provider "yandex" {
  token     = var.yc_token
  cloud_id  = var.yc_cloud_id
  folder_id = var.yc_folder_id
  zone      = var.zone
}

variable "yc_token" {
  type        = string
  description = "OAuth-token Yandex.Cloud"
  sensitive   = true
}
variable "yc_cloud_id" { type = string }
variable "yc_folder_id" { type = string }
variable "zone" {
  type    = string
  default = "ru-central1-a"
}

variable "ssh_user" {
  type    = string
  default = "ubuntu"
}

variable "ssh_pubkey_path" {
  type    = string
  default = "~/.ssh/id_rsa.pub"
}

resource "yandex_vpc_network" "snab" {
  name = "snabagent-vpc"
}

resource "yandex_vpc_subnet" "snab" {
  name           = "snabagent-subnet"
  zone           = var.zone
  network_id     = yandex_vpc_network.snab.id
  v4_cidr_blocks = ["10.10.0.0/24"]
}

resource "yandex_compute_instance" "snab" {
  name        = "snabagent-app"
  zone        = var.zone
  platform_id = "standard-v3"

  resources {
    cores         = 8
    memory        = 16
    core_fraction = 100
  }

  boot_disk {
    initialize_params {
      image_id = "fd87j7p2c3p3it2dr12i" # Ubuntu 22.04 LTS
      size     = 80
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.snab.id
    nat       = true
  }

  metadata = {
    user-data = templatefile("${path.module}/../ansible/cloud-init.yml", {
      ssh_user        = var.ssh_user
      ssh_public_key  = file(var.ssh_pubkey_path)
    })
    ssh-keys = "${var.ssh_user}:${file(var.ssh_pubkey_path)}"
  }
}

output "external_ip" {
  value = yandex_compute_instance.snab.network_interface.0.nat_ip_address
}
