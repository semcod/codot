<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# jak orchestrowac tego typu uslugi?

Usługi jak VIEW_BUNDLE (dashboard.php, FastAPI) orchestruj przez Service Registry + Saga/Workflow engine z Kubernetes/Docker Compose.  Pasuje do Twojego CQRS/Service Factory – dynamiczny deploy z rejestrem.[^1][^2][^3]

## Strategie orkiestracji

- **Registry-first**: Centralny rejestr (Consul/Etcd) – usługi self-register po starcie (port z output.port).[^4]
- **Saga Orchestration**: Koordynator (Temporal/Airflow) zarządza workflow (deploy → register → healthcheck).[^5][^2]
- **K8s Operators**: CRD dla BUNDLE – auto-deploy podów.[^6]


## Praktyczna implementacja

1. **Docker Compose** (dev/lokalnie):

```yaml
services:
  registry:
    image: consul
  dashboard:
    build: ./output  # z dashboard.php
    ports: ["8082:8082"]
    environment:
      - REGISTRY=consul:8500
    depends_on: [registry]
```

Usługa registeruje się: curl -X PUT registry/services/dashboard.
2. **Kubernetes** (prod):
    - Deployment z ConfigMap (JSON BUNDLE → env).
    - Service + HPA (scale wg load).
    - Operator: Watch CRD "ViewBundle" → apply manifests.[^6]
3. **Workflow Engine** (dynamiczne):


| Tool | Dla Ciebie | Zalety |
| :-- | :-- | :-- |
| Temporal | CQRS Sagas, Go/Python SDK [^2] | State machine dla depends_on |
| Airflow | DAG z BUNDLE sources [^1] | K8s native |
| Prefect | Microservices orchestration [^7] | Python-first |


## Kroki dla Ciebie

1. Dodaj do generatora: Dockerfile + register.sh (curl do Consul).
2. Service Registry w Factory: /register/{bundle_id} → Consul.
3. Saga: Temporal workflow "DeployViewBundle" (parse JSON → docker run → wait healthy → register).
4. Client: Query registry za serviceami, agreguj SSE.

Proxy: Caddy auto z Consul (dynamic routes).  Temporal pasuje do execute_node refaktoru.  Chcesz Temporal Go SDK przykład?[^2][^8][^4]
<span style="display:none">[^10][^11][^9]</span>

<div align="center">⁂</div>

[^1]: https://aya-space.vercel.app/blog/kubernetes-airflow-orchestration

[^2]: https://dev.to/coorayntl/saga-orchestration-in-net-with-cqrs-event-sourcing-hydration-event-propagation-2nof

[^3]: https://en.paradigmadigital.com/dev/architecture-patterns-microservices-communication-coordination/

[^4]: https://www.contentful.com/blog/microservices-orchestration/

[^5]: https://orbits.do/blog/workflows-orchestrate-microservices/

[^6]: https://github.com/apache/airflow-on-k8s-operator/blob/master/docs/design.md

[^7]: https://www.prefect.io/blog/microservices-orchestration-what-it-is-how-to-use-it

[^8]: https://www.perplexity.ai/search/864032a8-53be-4a8c-936c-7cf70c9bcfd6

[^9]: https://www.youtube.com/watch?v=VI_aRVBiDg8

[^10]: https://oneuptime.com/blog/post/2026-01-30-microservices-orchestration-pattern/view

[^11]: https://docs.ecotone.tech/modelling/business-workflows/orchestrators

