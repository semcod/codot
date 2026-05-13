"""kubernetes generator.

Emits Deployment + Service + optional ConfigMap for a bundle. Demonstrates
that the IR can target multiple infra backends.

No Ingress, no Istio — just Deployment + ClusterIP Service. Teams that
want ingress wire their own.
"""

from __future__ import annotations

from textwrap import dedent

from ...ir import Bundle


class KubernetesGenerator:
    target = "kubernetes"
    category = "infra"

    def generate(self, bundle: Bundle) -> dict[str, str]:
        return {
            "k8s/deployment.yaml": self._deployment(bundle),
            "k8s/service.yaml": self._service(bundle),
            "k8s/kustomization.yaml": self._kustomization(bundle),
        }

    def _deployment(self, bundle: Bundle) -> str:
        return dedent(f"""\
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: {bundle.name}
              labels:
                app: {bundle.name}
                version: "{bundle.version}"
                bundle-hash: "{bundle.contract_hash()}"
            spec:
              replicas: 1
              selector:
                matchLabels:
                  app: {bundle.name}
              template:
                metadata:
                  labels:
                    app: {bundle.name}
                    version: "{bundle.version}"
                spec:
                  containers:
                    - name: {bundle.name}
                      image: {bundle.name}:{bundle.version}
                      imagePullPolicy: IfNotPresent
                      ports:
                        - name: http
                          containerPort: {bundle.exposure.port}
                      env:
                        - name: SERVICE_NAME
                          value: "{bundle.name}"
                        - name: SERVICE_VERSION
                          value: "{bundle.version}"
                      resources:
                        limits:
                          cpu: "{bundle.resources.cpu}"
                          memory: "{bundle.resources.memory}"
                        requests:
                          cpu: "{bundle.resources.cpu}"
                          memory: "{bundle.resources.memory}"
                      livenessProbe:
                        httpGet:
                          path: {bundle.exposure.health_path}
                          port: http
                        initialDelaySeconds: 10
                        periodSeconds: 30
                      readinessProbe:
                        httpGet:
                          path: {bundle.exposure.health_path}
                          port: http
                        initialDelaySeconds: 2
                        periodSeconds: 10
        """)

    def _service(self, bundle: Bundle) -> str:
        return dedent(f"""\
            apiVersion: v1
            kind: Service
            metadata:
              name: {bundle.name}
              labels:
                app: {bundle.name}
            spec:
              type: ClusterIP
              selector:
                app: {bundle.name}
              ports:
                - name: http
                  port: 80
                  targetPort: http
        """)

    def _kustomization(self, bundle: Bundle) -> str:
        return dedent(f"""\
            apiVersion: kustomize.config.k8s.io/v1beta1
            kind: Kustomization
            labels:
              - pairs:
                  bundle: {bundle.name}
                  hash: "{bundle.contract_hash()}"
                includeSelectors: true
            resources:
              - deployment.yaml
              - service.yaml
        """)
