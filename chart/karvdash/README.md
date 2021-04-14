# Karvdash Helm Chart

[Karvdash](https://github.com/CARV-ICS-FORTH/karvdash) (Kubernetes CARV dashboard) is a dashboard service for facilitating data science on [Kubernetes](https://kubernetes.io). It supplies the landing page for working on a Kubernetes cluster, manages users, launches notebooks, and wires up relevant storage to the appropriate paths inside running containers.

Check out the [compatibility](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/README.md) notes before deploying.

## Deployment

Karvdash is deployed using [Helm](https://helm.sh) (version 3).

To install, you need a running Kubernetes environment with the following features:
* A private Docker registry. You can run one using the [official instructions](https://docs.docker.com/registry/deploying/), or use [this](https://artifacthub.io/packages/helm/twuni/docker-registry) Helm chart.
* The [cert-manager](https://cert-manager.io) certificate management controller for Kubernetes. This is used for creating certificates automatically for the admission webhooks. We use [this](https://artifacthub.io/packages/helm/jetstack/cert-manager) Helm chart.
* An [ingress controller](https://kubernetes.github.io/ingress-nginx/) answering to a domain name and its wildcard (i.e. both `example.com` and `*.example.com` should both point to your server). You can use [xip.io](http://xip.io) if you don't have a DNS entry. We use [this](https://artifacthub.io/packages/helm/ingress-nginx/ingress-nginx) Helm chart.
* For storage of Karvdash state, an existing persistent volume claim, or a directory in a shared filesystem mounted at the same path across all Kubernetes nodes, like NFS, [Gluster](https://www.gluster.org), or similar.
* For files, either a shared filesystem like the one used for storing the configuration, or access to an S3 service based on [MinIO](https://min.io).
* Optionally [Datashim](https://github.com/datashim-io/datashim), in which case Karvdash can be used to configure datasets (Datashim is required for files over S3).
* Optionally the [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack), for supporting the "Argo Metrics" template (a template that automatically creates a Prometheus/Grafana stack for collecting metrics from Argo). We use [this](https://artifacthub.io/packages/helm/prometheus-community/kube-prometheus-stack) Helm chart.

To deploy, first add the repo and then install. For example:

```bash
helm repo add karvdash https://carv-ics-forth.github.io/karvdash/chart
helm install karvdash karvdash/karvdash --namespace default \
    --set karvdash.ingressURL=https://example.com \
    --set karvdash.dockerRegistry=http://127.0.0.1:5000 \
    --set karvdash.stateHostPath=/mnt/nfs/karvdash \
    --set karvdash.filesURL=file:///mnt/nfs
```

Some of the variables set above are required. The table below lists all available options:

| Variable                          | Required | Description                                                                              | Default                           |
|-----------------------------------|----------|------------------------------------------------------------------------------------------|-----------------------------------|
| `image`                           |          | Docker image to use.                                                                     | `carvicsforth/karvdash:<version>` |
| `rbac.create`                     |          | Assign full permissions to Karvdash, API and namespace discovery to authenticated users. | `true`                            |
| `ingress.bodySize`                |          | The maximum allowed request size for the ingress.                                        | `4096m`                           |
| `karvdash.stateVolumeClaim`       | &check;  | If set, use this persistent volume claim for storing state.                              |                                   |
| `karvdash.stateHostPath`          | &check;  | The host path to use for storing state, when no existing volume claim is set.            |                                   |
| `karvdash.logsVolumeClaim`        |          | The volume to store HTTP access and error logs.                                          |                                   |
| `karvdash.logsHostPath`           |          | The host path to use for storing logs, when no existing volume claim is set.             |                                   |
| `karvdash.djangoSecret`           |          | Secret for Django. Use a random string of 50 characters.                                 | autogenerated                     |
| `karvdash.djangoDebug`            |          | Set to anything to enable, empty to disable.                                             |                                   |
| `karvdash.adminPassword`          |          | The default admin password.                                                              | `admin`                           |
| `karvdash.htpasswdExportDir`      |          | If set, the path to export the htpasswd file in.                                         |                                   |
| `karvdash.dashboardTitle`         |          | The title of the dashboard.                                                              | `Dashboard`                       |
| `karvdash.dashboardTheme`         |          | The theme of the dashboard. Choose between "evolve" and "CARV".                          | `evolve`                          |
| `karvdash.issuesURL`              |          | If set, an option to "Report an issue" is shown in the user menu.                        |                                   |
| `karvdash.ingressURL`             | &check;  | The ingress URL used.                                                                    |                                   |
| `karvdash.dockerRegistry`         |          | The URL of the Docker registry.                                                          | `http://127.0.0.1:5000`           |
| `karvdash.dockerRegistryNoVerify` |          | Set to anything to skip Docker registry SSL verification.                                |                                   |
| `karvdash.datasetsAvailable`      |          | Set to anything to enable dataset management.                                            |                                   |
| `karvdash.filesURL`               | &check;  | The base URL for the private and shared file domains.                                    |                                   |
| `karvdash.allowedHostPathDirs`    |          | Other host paths to allow attaching to containers (separate with `:`).                   |                                   |

Set `karvdash.filesURL` to:
* `file://<path>`, if using a node-wide, shared mountpoint for user files. Karvdash will create `private/<username>` and `shared` folders within.
* `minio://<accessKeyID>:<secretAccessKey>@<host>:<port>/<prefix>` or `minios://...`, to use MinIO for files (`minios` for MinIO over SSL). Karvdash will create `<prefix>-private-<userrname>` and `<prefix>-shared` buckets within.

The state volume is used to store the database, the running services repository, and the template library. You can either use an existing peristent storage claim with `karvdash.stateVolumeClaim`, or set `karvdash.stateHostPath` to automatically create one (this must accessible by all nodes). Create a `templates` directory inside the state volume to add new service templates or override defaults (the ones in [templates](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/templates)). Templates placed there will be available as read-only to all users.

To remove Karvdash, uninstall using `helm uninstall karvdash`, which will remove the service, admission webhooks, and RBAC rules, but not associated CRDs. You can use the YAML files in [crds](https://github.com/CARV-ICS-FORTH/karvdash/tree/master/chart/karvdash/crds) to remove them.