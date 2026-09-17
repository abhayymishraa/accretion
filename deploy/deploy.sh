#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

sha=${1:?Provide the commit SHA}
domain=${2:?Provide the backend domain}
template_ref=${3-}
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 2
[[ "$domain" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || exit 2
if [[ -n "$template_ref" ]] && [[ ! "$template_ref" =~ ^[a-z0-9][a-z0-9_-]*(/[a-z0-9][a-z0-9_-]*)?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
    echo 'Invalid E2B template reference; use template-name:<exact-build-UUID>'
    exit 2
fi
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
for key in DATABASE_URL OPENAI_API_KEY E2B_API_KEY E2B_TEMPLATE_ID STORAGE_BUCKET; do
    grep -qE "^${key}=.+$" "$root/runtime.env" || { echo "Missing $key"; exit 1; }
done
grep -qE '^STORAGE_PROVIDER=gcs$' "$root/runtime.env" || { echo 'Production requires STORAGE_PROVIDER=gcs'; exit 1; }
grep -qE '^GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcs.json$' "$root/runtime.env" || { echo 'Set GOOGLE_APPLICATION_CREDENTIALS to the mounted credential path'; exit 1; }
[[ -s "$root/secrets/gcs.json" ]] || { echo 'Missing private GCS credentials file'; exit 1; }
chown 10001:10001 "$root/secrets/gcs.json"
chmod 400 "$root/secrets/gcs.json"
grep -qE '^SECRET_KEY=.{32,}$' "$root/runtime.env" || { echo 'SECRET_KEY must contain at least 32 characters'; exit 1; }
previous=$(readlink -f "$root/current" 2>/dev/null || true)
[[ -f "$previous/compose.yaml" ]] || previous=
[[ "$previous" != "$release" ]] || { echo 'This release is already deployed'; exit 0; }
previous_template_ref=$(sed -n 's/^E2B_TEMPLATE_ID=//p' "$root/runtime.env")
runtime_changed=false

compose() {
    local directory=$1
    shift
    docker compose -p webbuilder --env-file "$directory/deployment.env" \
        -f "$directory/compose.yaml" "$@"
}

rollback() {
    local status=$?
    trap - ERR INT TERM
    echo 'Deployment failed; restoring the previous release.'
    if [[ "$runtime_changed" == true ]]; then
        runtime_tmp=$(mktemp "$root/runtime.env.XXXXXX")
        awk -v value="$previous_template_ref" '
            /^E2B_TEMPLATE_ID=/ { print "E2B_TEMPLATE_ID=" value; found=1; next }
            { print }
            END { if (!found) print "E2B_TEMPLATE_ID=" value }
        ' "$root/runtime.env" > "$runtime_tmp"
        chown --reference="$root/runtime.env" "$runtime_tmp"
        chmod --reference="$root/runtime.env" "$runtime_tmp"
        mv -f "$runtime_tmp" "$root/runtime.env"
    fi
    if [[ -n "$previous" ]]; then
        compose "$previous" up -d --remove-orphans || true
    else
        compose "$release" stop api || true
    fi
    rm -f "$artifact_dir/backend-image.tar.gz"
    exit "$status"
}

mkdir -p "$release"
cp "$artifact_dir/deploy/compose.yaml" "$artifact_dir/deploy/Caddyfile" "$release/"
printf 'BACKEND_IMAGE=%s\nBACKEND_DOMAIN=%s\n' "$image" "$domain" > "$release/deployment.env"
# Load the CI-built artifact. No compiler, package installation or Git checkout on this VM.
docker load --input "$artifact_dir/backend-image.tar.gz"
rm -f "$artifact_dir/backend-image.tar.gz"
docker image inspect "$image" >/dev/null
compose "$release" config --quiet
compose "$release" pull proxy
trap rollback ERR
trap 'false' INT TERM
if [[ -n "$template_ref" ]] && [[ "$template_ref" != "$previous_template_ref" ]]; then
    runtime_tmp=$(mktemp "$root/runtime.env.XXXXXX")
    awk -v value="$template_ref" '
        /^E2B_TEMPLATE_ID=/ { print "E2B_TEMPLATE_ID=" value; found=1; next }
        { print }
        END { if (!found) print "E2B_TEMPLATE_ID=" value }
    ' "$root/runtime.env" > "$runtime_tmp"
    chown --reference="$root/runtime.env" "$runtime_tmp"
    chmod --reference="$root/runtime.env" "$runtime_tmp"
    mv -f "$runtime_tmp" "$root/runtime.env"
    runtime_changed=true
fi
# Drain the old writer before migrating legacy event arrays into ordered rows.
if [[ -n "$previous" ]]; then compose "$previous" stop api; fi
docker run --rm --env-file "$root/runtime.env" "$image" python -m db.migrate
compose "$release" up -d --no-deps api

healthy=false
for attempt in $(seq 1 60); do
    container=$(compose "$release" ps -q api)
    if [[ -n "$container" ]] && [[ $(docker inspect --format '{{.State.Health.Status}}' "$container") == healthy ]]; then
        healthy=true
        break
    fi
    sleep 3
done
[[ "$healthy" == true ]]
compose "$release" up -d --no-deps proxy
# Verify routing through the proxy without depending on public DNS propagation.
curl --fail --silent --show-error --retry 5 --retry-connrefused --retry-delay 2 \
    --max-time 15 http://127.0.0.1:8000/health/ready >/dev/null
curl --fail --silent --show-error --retry 10 --retry-all-errors --retry-delay 6 \
    --resolve "$domain:443:127.0.0.1" --max-time 15 "https://$domain/health/ready" >/dev/null
ln -sfn "$release" "$root/current.next"
mv -Tf "$root/current.next" "$root/current"
trap - ERR INT TERM

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
