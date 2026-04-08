# Gunicorn + systemd Deployment

## Files
- `deploy/gunicorn.conf.py`: Gunicorn runtime config.
- `deploy/fair-review.service`: systemd root service unit.
- `deploy/user/fair-review.service`: systemd user service unit.
- `scripts/install_systemd_service.sh`: one-time install + enable + restart.
- `scripts/systemd_service.sh`: day-to-day service management.
- `scripts/install_user_systemd_service.sh`: one-time install for `systemd --user`.
- `scripts/user_systemd_service.sh`: day-to-day user service management.

## One-time setup (root systemd)
```bash
cd /home/user/progect/FairReviewSystem
bash scripts/install_systemd_service.sh
```

## Daily operations (root systemd)
```bash
bash scripts/systemd_service.sh status
bash scripts/systemd_service.sh restart
bash scripts/systemd_service.sh logs
```

## One-time setup (user systemd, no sudo)
```bash
cd /home/user/progect/FairReviewSystem
bash scripts/install_user_systemd_service.sh
```

## Daily operations (user systemd)
```bash
bash scripts/user_systemd_service.sh status
bash scripts/user_systemd_service.sh restart
bash scripts/user_systemd_service.sh logs
```

## Nginx reverse proxy
```bash
cd /home/user/progect/FairReviewSystem
bash scripts/install_nginx_site.sh
```

Common operations:
```bash
bash scripts/nginx_site.sh test
bash scripts/nginx_site.sh reload
bash scripts/nginx_site.sh status
```

## Notes
- Service binds to `127.0.0.1:5000`.
- Runtime uses dedicated virtualenv: `/home/user/progect/FairReviewSystem/.venv-deploy`.
- Logs are written to:
  - `/tmp/fair_review_access.log`
  - `/tmp/fair_review_error.log`
- Environment variables are loaded from `.env` by both systemd (`EnvironmentFile`) and app runtime.
