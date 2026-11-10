# Weitere Provider ergänzen

1. Implementierten Compute-Adapter neben compute/hetzner anlegen und den [Outputvertrag](architecture/provider-abstraction.md) erfüllen. Keine leeren Platzhalter für unimplementierte Clouds einchecken.
2. Root-Modul für die neue Providerkombination definieren und die bisherige Konfiguration validiert auf image/region/server_type/Firewall/SSH abbilden. CLI-Rootauswahl an zentraler Stelle in lib/config.sh ergänzen, Ansible-Inventarvertrag unverändert lassen.
3. AWS EC2 braucht VPC/Subnet, Security Group, AMI, EBS-Verschlüsselung und Instance Profile. Azure braucht Resource Group, VNet/Subnet, NSG, NIC/Public-IP und Managed Identity. GCE benötigt Projekt, VPC/Firewall, Machine Type und Service Account. Alibaba ECS benötigt VPC/VSwitch, Security Group, ECS-Image/Instance Type und RAM-Rolle. DigitalOcean benötigt Droplet, SSH-Key und Cloud-Firewall. Diese Varianten sind nicht implementiert und werden von cloud_provider zunächst abgelehnt.
4. S3-Adapter bei Bedarf auf AWS S3 oder einen anderen kompatiblen Dienst ändern; Endpoint, Region, Bucket, Auth und Verschlüsselungs-/Retentionsemantik testen. Azure Blob ist kein S3-Drop-in; Restic-Backend und Credentials ausdrücklich ändern.
5. DNS-/Edge-Adapter unabhängig austauschen. CloudFront oder Azure Front Door haben andere Zertifikats-/Origin- und Trust-Modelle. ACME-DNS-Plugin und Firewall-/Client-IP-Vertrauen mitwechseln. Für andere DNS-Provider den Certbot-Adapter in der application-Rolle ersetzen.
6. Pinning/Lockdateien, Mockvertragsprüfungen, Terraform validate und echten isolierten Deployment-/DR-Test durchführen. Cloud-Wechsel als Migration planen, keine bestehenden Ressourcen implizit ersetzen.

Module werden gemeinsam über Repository-Tags versioniert. Bei Auslagerung in externe Modul-Repositories immutable ref/Version angeben und Outputvertrag beibehalten. HCP-State-Backend und Environment-Konventionen bleiben davon unabhängig.
