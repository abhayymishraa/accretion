#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

sha=${1:?Provide the commit SHA}
domain=${2:?Provide the backend domain}
# Optional second hostname, served alongside the primary during a migration.
domain_alt=${3-}
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 2
[[ "$domain" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || exit 2
[[ -z "$domain_alt" || "$domain_alt" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || exit 2
[[ $(id -u) == 0 ]] || { echo 'Run with sudo'; exit 2; }

artifact_dir=$(cd "$(dirname "$0")/.." && pwd)
root=/opt/webbuilder
release="$root/releases/$sha"
image="webbuilder-backend:$sha"
mkdir -p "$root/releases" "$root/projects"
chown 10001:10001 "$root/projects"
exec 9>"$root/deploy.lock"
flock -w 300 9
[[ -s "$root/runtime.env" ]] || { echo 'Missing runtime.env'; exit 1; }
# The app itself rejects an unknown DEFAULT_MODEL or a missing provider key at boot,
# which fails the health check below.
for key in DATABASE_URL DEFAULT_MODEL E2B_API_KEY STORAGE_BUCKET; do
    grep -qE "^${key}=.+$" "$root/runtime.env" || { echo "Missing $key"; exit 1; }
done
# The template as name:tag (for example accretion:production); `make template-build` moves the tag.
grep -qE "^E2B_TEMPLATE=[a-z0-9][a-z0-9_-]*:[A-Za-z0-9._-]+$" "$root/runtime.env" \
    || { echo "Missing or invalid E2B_TEMPLATE; use template-name:tag"; exit 1; }
grep -qE '^STORAGE_PROVIDER=gcs$' "$root/runtime.env" || { echo 'Production requires STORAGE_PROVIDER=gcs'; exit 1; }
grep -qE '^GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcs.json$' "$root/runtime.env" || { echo 'Set GOOGLE_APPLICATION_CREDENTIALS to the mounted credential path'; exit 1; }
[[ -s "$root/secrets/gcs.json" ]] || { echo 'Missing private GCS credentials file'; exit 1; }
chown 10001:10001 "$root/secrets/gcs.json"
chmod 400 "$root/secrets/gcs.json"
grep -qE '^SECRET_KEY=.{32,}$' "$root/runtime.env" || { echo 'SECRET_KEY must contain at least 32 characters'; exit 1; }
previous=$(readlink -f "$root/current" 2>/dev/null || true)
[[ -f "$previous/compose.yaml" ]] || previous=
[[ "$previous" != "$release" ]] || { echo 'This release is already deployed'; exit 0; }

compose() {
    local directory=$1
    shift
    docker compose -p webbuilder --env-file "$directory/deployment.env" \
        -f "$directory/compose.yaml" "$@"
}

rollback() {
    local status=$?
    trap - ERR INT TERM
    echo 'Deployment failed; the previous release keeps serving.'
    if [[ -n "${new_api:-}" ]]; then
        docker inspect --format 'API health diagnostics: {{json .State.Health}}' "$new_api" || true
        echo 'API container logs:'
        docker logs --tail 50 "$new_api" || true
        # The old container never stopped, so removing the new one is the whole rollback.
        docker rm -f "$new_api" || true
    fi
    if [[ -n "$previous" ]]; then
        install -m 644 "$previous/Caddyfile" "$root/caddy/Caddyfile" || true
        reload_proxy "$previous" || true
    fi
    rm -f "$artifact_dir/backend-image.tar.gz"
    exit "$status"
}

# Applies the Caddyfile in $root/caddy without restarting Caddy, so open connections stay up.
reload_proxy() {
    compose "$1" up -d --no-deps proxy
    compose "$1" exec -T proxy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
}

mkdir -p "$release"
cp "$artifact_dir/deploy/compose.yaml" "$artifact_dir/deploy/Caddyfile" "$release/"
printf 'BACKEND_IMAGE=%s\nBACKEND_DOMAIN=%s\nBACKEND_DOMAIN_ALT=%s\n' \
    "$image" "$domain" "$domain_alt" > "$release/deployment.env"
# Load the CI-built artifact. No compiler, package installation or Git checkout on this VM.
docker load --input "$artifact_dir/backend-image.tar.gz"
rm -f "$artifact_dir/backend-image.tar.gz"
docker image inspect "$image" >/dev/null
compose "$release" config --quiet
compose "$release" pull proxy
trap rollback ERR
trap 'false' INT TERM
# The previous release keeps serving while the schema migrates, so a migration must work with it
# still running (AGENTS.md).
docker run --rm --env-file "$root/runtime.env" "$image" alembic upgrade head
# --no-deps skips depends_on, so Redis is started on its own. An unchanged service is left running,
# so its queue and channels survive a normal deploy.
compose "$release" up -d --no-deps redis

# Zero downtime: the new api container starts beside the running one, Caddy routes to both, and
# the old one stops only once the new one is healthy and reachable through the proxy.
old_api=$(docker ps -q --no-trunc --filter label=com.docker.compose.project=webbuilder \
    --filter label=com.docker.compose.service=api)
running=$(grep -c . <<<"$old_api" || true)
compose "$release" up -d --no-deps --no-recreate --scale api=$((running + 1)) api
new_api=$(compose "$release" ps -q api | grep -vxF -f <(printf '%s\n' "${old_api:-none}"))
(( $(wc -l <<<"$new_api") == 1 ))

healthy=false
for attempt in $(seq 1 90); do
    if [[ $(docker inspect --format '{{.State.Health.Status}}' "$new_api") == healthy ]]; then
        healthy=true
        break
    fi
    sleep 2
done
[[ "$healthy" == true ]]
mkdir -p "$root/caddy"
install -m 644 "$release/Caddyfile" "$root/caddy/Caddyfile"
reload_proxy "$release"
# Verify routing through the proxy without depending on public DNS propagation.
curl --fail --silent --show-error --retry 10 --retry-all-errors --retry-delay 3 \
    --resolve "$domain:443:127.0.0.1" --max-time 15 "https://$domain/health/ready" >/dev/null
ln -sfn "$release" "$root/current.next"
mv -Tf "$root/current.next" "$root/current"
trap - ERR INT TERM

# The new release serves; now the old container goes. Requests in flight finish within its graceful
# timeout, and Caddy retries any that reach it while stopping on the new one. A failure here leaves
# both running, which the next deploy cleans up, so it does not fail this one.
if [[ -n "$old_api" ]]; then
    xargs docker stop --time 40 <<<"$old_api" >/dev/null || echo 'Old api container did not stop'
    xargs docker rm <<<"$old_api" >/dev/null || echo 'Old api container was not removed'
fi

# Keep the current and previous image for rollback; only remove this app's older tags.
previous_image=
if [[ -n "$previous" ]]; then
    previous_image=$(sed -n 's/^BACKEND_IMAGE=//p' "$previous/deployment.env")
    printf '%s\n' "$previous" > "$root/previous-release"
fi
while read -r candidate; do
    if [[ "$candidate" != "$image" && "$candidate" != "$previous_image" ]]; then
        docker image rm "$candidate" >/dev/null || true
    fi
done < <(docker image ls webbuilder-backend --format '{{.Repository}}:{{.Tag}}')
echo "Deployed $sha"
