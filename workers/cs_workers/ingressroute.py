from kubernetes import client


class IngressRouteApi:
    def __init__(self,):
        self.client = client.CustomObjectsApi()
        self.group = "traefik.containo.us"
        self.version = "v1alpha1"

    def create_namespaced_ingressroute(self, namespace, body, **kwargs):
        return self.client.create_namespaced_custom_object(
            self.group, self.version, namespace, "ingressroutes", body=body
        )

    def get_namespaced_ingressroute(self, name, namespace):
        return self.client.get_namespaced_custom_object(
            self.group, self.version, namespace, "ingressroutes", name
        )

    def patch_namespaced_ingressroute(self, name, namespace, body):
        return self.client.patch_namespaced_custom_object(
            self.group, self.version, namespace, "ingressroutes", name, body=body
        )

    def delete_namespaced_ingressroute(self, name, namespace, **kwargs):
        return self.client.delete_namespaced_custom_object(
            self.group, self.version, namespace, "ingressroutes", name, **kwargs
        )


def ingressroute_template(namespace, name, routes, tls=True):
    if tls:
        tls_config = {"tls": {"certResolver": "myresolver"}}
    else:
        tls_config = {}
    return {
        "apiVersion": "traefik.containo.us/v1alpha1",
        "kind": "IngressRoute",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"entryPoints": ["websecure"], "routes": routes, **tls_config},
    }
