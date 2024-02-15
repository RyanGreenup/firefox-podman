#!/bin/sh
# All the options for safety
# set -euf -o pipefail
set -euf



container_name=firefox

# Build the container
# podman build -t "${container_name}" . || \
#     { echo "Unable to build"; exit 1; }

# If using X
# xhost +SI:localuser:$(whoami)
# xhost +SI:localuser:root  # Required if you're running the container as root

# podman run --rm -it \
#  --net=host \
#  --env="DISPLAY=${DISPLAY}" \
#  --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
#  --security-opt label=type:container_runtime_t \
# "${container_name}"

# xhost -


#   - `--rm` automatically cleans up the container and removes the file system when the container exits.
#   - `-it` allows you to interact with Firefox.
#   - `--net=host` lets the container share the host's networking namespace.
#   - `--env` sets the `$DISPLAY` environment variable to direct X11 to the appropriate display screen of the host.
#   - `--volume` mounts the X11 Unix socket so Firefox can use the host's display.
#   - `--security-opt label=type:container_runtime_t` might be necessary to allow Firefox to connect to the X display server depending upon SELinux policies.



# Wayland

# podman run --rm -it \
#   --env="DISPLAY=${DISPLAY}" \
#   --env="MOZ_ENABLE_WAYLAND=1" \
#   --volume="/run/user/${UID}/wayland-0:/run/user/${UID}/wayland-0" \
#   -v /tmp/.X11-unix:/tmp/.X11-unix \
#   --volume="${XDG_RUNTIME_DIR}/pulse/native:${XDG_RUNTIME_DIR}/pulse/native" \
#   --volume="/run/user/${UID}/wayland-0:/run/user/${UID}/wayland-0" \
#   --security-opt label=type:container_runtime_t \
#   --net=host \
#   --device /dev/snd \
#   "${container_name}"

# the sound is added by adding the `--device /dev/snd` option to the `podman run` command. This option allows the container to access the sound card on the host system.


# Use this for wayland
#   --env="MOZ_ENABLE_WAYLAND=1" \
# podman run -d \
#     --net host \
#     --security-opt label=type:container_runtime_t \
#     -e DISPLAY=$DISPLAY \
#     -e PULSE_SERVER=unix:${XDG_RUNTIME_DIR}/pulse/native \
#     -v /tmp/.X11-unix:/tmp/.X11-unix \
#     -v ${XDG_RUNTIME_DIR}/pulse/native:${XDG_RUNTIME_DIR}/pulse/native \
#     "${container_name}"

# also --net host for webapp container
# good security to have different username in container
# however, need to remember to make one in dockerfile
UNAME=user
UUID=$(id -u)
GUID=$(id -u)
FF_IMAGE=localhost/firefox
CONTAINER=podman
if [ "podman" == "${CONTAINER}" ]; then
    USER_NS="--userns=keep-id"
fi
# UNAME=$(id -u -n)

# TODO test if XAUTHORITY exists first
# -v ${XAUTHORITY}:${XAUTHORITY} \
# -e XAUTHORITY \
# -v ${HOME}/.Xauthority:/home/${UNAME}/.Xauthority:Z \

# --device /dev/video0 \
# ${CONTAINER} --log-level=debug run -ti \
#         ${USER_NS} \
# 		--security-opt label=type:container_runtime_t \
# 		--net=host -d --rm \
# 		-v /tmp/.X11-unix:/tmp/.X11-unix \
# 		-v /dev/dri:/dev/dri \
# 		-e DISPLAY \
# 		-v ${HOME}/.config/pulse/cookie:/home/${UNAME}/.config/pulse/cookie \
# 		-v /etc/machine-id:/etc/machine-id \
# 		-v /run/user/${UUID}/pulse:/run/user/${UUID}/pulse \
# 		-v /var/lib/dbus:/var/lib/dbus \
# 		--device /dev/snd \
# 		-e PULSE_SERVER=unix:${XDG_RUNTIME_DIR}/pulse/native \
# 		-v ${XDG_RUNTIME_DIR}/pulse/native:${XDG_RUNTIME_DIR}/pulse/native \
#         -v ${HOME}/.local/share/containerized_apps/firefox-webapp:/home/${UNAME} \
#         -v ${HOME}/Downloads:/home/${UNAME}/Downloads \
#         ${FF_IMAGE} \bin\sh

# and in the container I set the new user as 1000:1000
# I'll make a script where this is a global variable
#

home_xauth="${HOME}/.Xauthority"
if [ -f ${home_xauth}  ]; then
  home_xauth="-v ${home_xauth}:/home/${UNAME}/.Xauthority:Z"
else
    home_xauth=""
fi


if [ -n "${XDG_RUNTIME_DIR+1}" ]; then
    mount_xdg_runtime_dir="-v ${XDG_RUNTIME_DIR}:${XDG_RUNTIME_DIR}:Z"

    # Wayland only works if XDG is set
    if [ "${XDG_SESSION_TYPE:-}" == "wayland" ]; then
       WAYLAND="-e MOZ_ENABLE_WAYLAND=1"

       # uncomment for x11 passthrough
       unset DISPLAY
    else
        WAYLAND=""
    fi
fi


# Note that -e env var passthrough allows unset variables
# so we can include DISPLAY and XDG_RUNTIME_DIR eve if they are not set
podman run --rm -ti  \
    --userns=keep-id \
    --user=1000:1000 \
	--security-opt label=type:container_runtime_t \
    --net=host \
    ${home_xauth} \
        -w /home/${UNAME} \
		-v /tmp/.X11-unix:/tmp/.X11-unix \
 		-v /dev/dri:/dev/dri \
  		-e DISPLAY \
        -e WAYLAND_DISPLAY \
        -e XDG_RUNTIME_DIR \
        ${mount_xdg_runtime_dir} \
        ${WAYLAND} \
  		-v ${HOME}/.config/pulse/cookie:/home/${UNAME}/.config/pulse/cookie \
  		-v /etc/machine-id:/etc/machine-id \
  		-v /run/user/${UUID}/pulse:/run/user/${UUID}/pulse \
  		-v /var/lib/dbus:/var/lib/dbus \
  		--device /dev/snd \
  		-e PULSE_SERVER=unix:${XDG_RUNTIME_DIR}/pulse/native \
  		-v ${XDG_RUNTIME_DIR}/pulse/native:${XDG_RUNTIME_DIR}/pulse/native \
         -v ${HOME}/.local/share/containerized_apps/firefox-arkenfox-alpine:/home/${UNAME}:Z \
          -v ${HOME}/Downloads:/home/${UNAME}/Downloads:Z \
  -v ${XAUTHORITY}:${XAUTHORITY} \
  -e XAUTHORITY \
 	  ${FF_IMAGE} \
     firefox --profile /home/${UNAME}/.mozilla/firefox/main_profile --new-instance
     # /bin/sh

#     localhost/firefox /bin/sh

#  firefox -p main_profile

# there are two dockerfiles
# /home/ryan/Sync/Projects/2024/docker-container-apps/firefox-container/Dockerfile_alpine
# /home/ryan/Sync/Config/DotFiles/container-dockerfiles/applications/arch/ff_in_podman
