#!/bin/sh
set -euf

UNAME=user
UUID=$(id -u)
GUID=$(id -u)
IMAGE=localhost/firefox
CONT=firefox
CONTAINER=podman
if [ "podman" == "${CONTAINER}" ]; then
    USER_NS="--userns=keep-id"
fi

# Mount the Xauthority file if it exists
home_xauth="${HOME}/.Xauthority"
if [ -f ${home_xauth}  ]; then
  home_xauth="-v ${home_xauth}:/home/${UNAME}/.Xauthority:Z"
else
    home_xauth=""
fi

# Mount the XDG Runtime Directory if it exists
if [ -n "${XDG_RUNTIME_DIR+1}" ]; then
    mount_xdg_runtime_dir="-v ${XDG_RUNTIME_DIR}:${XDG_RUNTIME_DIR}:Z"

    # Wayland only works if XDG is set
    # Enable Wayland if it is in use by host
    if [ "${XDG_SESSION_TYPE:-}" == "wayland" ]; then
       WAYLAND="-e MOZ_ENABLE_WAYLAND=1"

       # Unset this to force the issue, uncomment to permit x11
       # unset DISPLAY
    else
        WAYLAND=""
    fi
fi


# Note that -e env var passthrough allows unset variables
# so we can include DISPLAY and XDG_RUNTIME_DIR eve if they are not set
podman run --rm -ti  \
    ${USER_NS} \
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
 	  ${IMAGE} \
     firefox --profile /home/${UNAME}/.mozilla/firefox/main_profile --new-instance
     # /bin/sh
