# moniflow
DevOps Monitoring


```bash
docker compose up --build
docker exec -it moniflow-alert_service-1 sh -c "PYTEST_RUNNING=true pytest tests/ -v"

```