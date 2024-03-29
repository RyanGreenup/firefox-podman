# These are what distrobox uses, we don't need them, here for debugging

deps="
    alpine-base
    bash
    bash-completion
    bc
    bzip2
    coreutils
    curl
    diffutils
    docs
    findmnt
    findutils
    gcompat
    gnupg
    gpg
    iproute2
    iputils
    keyutils
    less
    libc-utils
    libcap
    lsof
    man-pages
    mandoc
    mount
    musl-utils
    ncurses
    ncurses-terminfo
    net-tools
    openssh-client
    pigz
    pinentry
    posix-libc-utils
    procps
    rsync
    shadow
    su-exec
    sudo
    tar
    tcpdump
    tree
    tzdata
    umount
    unzip
    util-linux
    util-linux-misc
    vte3
    wget
    which
    xauth
    xz
    zip
    $(apk search -q mesa-dri)
    $(apk search -q mesa-vulkan)
    vulkan-loader
"
install_pkg=""
for dep in ${deps}; do
    if apk info "${dep}" > /dev/null; then
        install_pkg="${install_pkg} ${dep}"
    fi
done
