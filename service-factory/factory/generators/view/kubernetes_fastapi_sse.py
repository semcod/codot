from __future__ import annotations

from textwrap import dedent

from ...ir import AnyBundle, ViewBundle
from ._shared import uses_host_local_sources


class KubernetesFastApiSseViewGenerator:
    target = "view/kubernetes-fastapi-sse"
    category = "view"

    def generate(self, bundle: AnyBundle) -> dict[str, str]:
        if not isinstance(bundle, ViewBundle):
            raise TypeError(
                f"{self.target} expects a ViewBundle, got {type(bundle).__name__}"
            )
        return {
            "k8s/deployment.yaml": self._deployment(bundle),
            "k8s/service.yaml": self._service(bundle),
            "k8s/kustomization.yaml": self._kustomization(bundle),
        }

    def _deployment(self, bundle: ViewBundle) -> str:
        host_local = uses_host_local_sources(bundle)
        host_network = "\n                  hostNetwork: true" if host_local else ""
        dns_policy = (
            "\n                  dnsPolicy: ClusterFirstWithHostNet" if host_local else ""
        )
        return dedent(
            f"""\
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
                spec:{host_network}{dns_policy}
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
                        - name: VIEW_TRANSPORT
                          value: "sse"
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
            """
        )

    def _service(self, bundle: ViewBundle) -> str:
        return dedent(
            f"""\
            apiVersion: v1
            kind: Service
            metadata:
              name: {bundle.name}
              labels:
                app: {bundle.name}
                bundle-hash: "{bundle.contract_hash()}"
            spec:
              type: ClusterIP
              selector:
                app: {bundle.name}
              ports:
                - name: http
                  port: 80
                  targetPort: http
            """
        )

    def _kustomization(self, bundle: ViewBundle) -> str:
        return dedent(
            f"""\
            apiVersion: kustomize.config.k8s.io/v1beta1
            kind: Kustomization
            labels:
              - pairs:
                  bundle: {bundle.name}
                  hash: "{bundle.contract_hash()}"
                  category: view
                includeSelectors: true
            resources:
              - deployment.yaml
              - service.yaml
            """
        )
