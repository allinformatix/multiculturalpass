# DNS, Edge und TLS

Cloudflare verwaltet zunächst einen A-Record auf den IPv4-Origin. DNS-Zone/Delegation müssen existieren. Proxy-Modus ist konfigurierbar. Origin-TLS ist ein separates öffentlich vertrauenswürdiges Let's-Encrypt-Zertifikat via Certbot DNS-01; es funktioniert auch ohne Cloudflare-Proxy. Renewals laufen über certbot.timer und validierten NGINX-Reload. Ablaufdatum überwachen. Kein Origin-CA-Zertifikat und kein unverschlüsseltes Full/Flexible-Backend.

Bei Proxy-Nutzung Cloudflare auf **Full (strict)** und mindestens TLS 1.2 setzen. `manage_zone_settings=true` verwaltet diese Einstellungen zonenweit; ausschließlich einen Environment-State dafür einsetzen. Bei externer Verwaltung Einstellung vor Erstbetrieb direkt im Cloudflare-Dashboard prüfen. DNS-Token für Certbot darf nur DNS in der gewählten Zone bearbeiten und die Zone lesen.

Odoo ist dynamisch. NGINX setzt Cache-Control private,no-store und verwendet keinen proxy_cache. Zusätzlich Cache Rules mit cache=false für ALLE Odoo-Hostnames setzen; kein Cache Everything und kein APO für diese Hosts. Ein bestehendes Cache-Entrypoint-Ruleset muss erweitert/importiert werden; mehrere Terraform-States dürfen nicht dieselbe Zone/Phase verwalten. manage_cache_rules ist deshalb standardmäßig aus und der Betreiber muss externe Regeln ausdrücklich bestätigen. Enterprise-/Paid-WAF- und Rate-Limit-Rules sind optionale Erweiterungen; deren Existenz wird nicht behauptet.

WebSocket-/Longpolling-Routen gehen an Port 8072, normale HTTP-Anfragen an 8069. Ein HTTP-Worker aktiviert den separaten Evented-Worker. Details: [Odoo Deployment](https://www.odoo.com/documentation/18.0/administration/on_premise/deploy.html). CDN-/Origin-Timeouts begrenzen lange Requests unabhängig vom NGINX-Timeout; große Jobs asynchron ausführen.

Der Origin akzeptiert im Proxy-Modus nur Cloudflare-Quellnetze. NGINX vertraut CF-Connecting-IP ausschließlich aus diesen Netzen und ersetzt weitere Forwarding-Header. Das Login-Limit gilt so pro Client statt pro Cloudflare-PoP. DNS-only vertraut keinem gelieferten Client-IP-Header. Die eingecheckten [IPv4](https://www.cloudflare.com/ips-v4/)- und [IPv6](https://www.cloudflare.com/ips-v6/)-Netze bei Updates gegen offizielle Listen prüfen und gemeinsam in Firewall/NGINX ausrollen. Lokale Proxy-Checks nutzen `https://HOST --resolve HOST:443:127.0.0.1` auf dem Server.

Ein zukünftiger CloudFront-/Front-Door-Adapter muss DNS, Edge-Zertifikat, Origin-Zertifikat, Origin-Zugriff und vertrauenswürdige Header getrennt implementieren. DNS-Austausch allein ersetzt diese Sicherheitsgrenzen nicht.
