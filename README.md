# suse-module-tools

This package contains a collection of tools and configuration files for
handling kernel modules and setting module parameters. The configuration files
represent a carefully engineered, recommended default configuration. In
certain cases, it may be necessary to modify or revert some of these settings.
It's ok to do so, but make sure you know what you're doing if you do.

Please don't edit any of the configuration files shipped in this package.
Instead, copy the files from `/lib/modprobe.d` to `/etc/modprobe.d`, preserving
the file name, and edit the copy under `/etc/modprobe.d`.
Likewise for `/lib/depmod.d` vs. `/etc/depmod.d` and `/usr/lib/modules-load.d` vs.
`/etc/modules-load.d`.

To completely mask the directives in a configuration file, it's recommended
to create a symlink to /dev/null with the same name as the file to be masked 
in the respective directory under `/etc`. E.g. to mask 
`/lib/modprobe.d/20-foo.conf`, run

    ln -s /dev/null /etc/modprobe.d/20-foo.conf


## Blacklisted file systems

In the Linux kernel, file system types are implemented as kernel
modules. While many of these file systems are well maintained, some of the
older and less frequently used ones are not. This poses a security risk,
because maliciously crafted file system images might open security holes when
mounted either automatically or by an inadvertent user. 

These file systems are therefore **blacklisted** by default under openSUSE and
SUSE Enterprise Linux. This means that the on-demand loading of file system
modules at mount time is disabled. Blacklisting is accomplished by placing
configuration files called `60-blacklist_fs-$SOME_FS.conf` under
`/lib/modprobe.d`. The current list of blacklisted filesystems is:

    @FS_BLACKLIST@ # will be filled from spec file during package build

### CAVEAT

In the very unlikely case that one of the blacklisted file systems is necessary
for your system to boot, make sure you un-blacklist your file system before
rebooting.

### Un-blacklisting a file system

If a user tries to **mount(8)** a device with a blacklisted file system, the
mount command prints an error message like this:

    mount: /mnt/mx: unknown filesystem type 'minix' (hint: possibly blacklisted, see mount(8)).

(**mount(8)** can't distinguish between a file system for which no kernel
module exists at all, and a file system for which a module exists which
is blacklisted).

Users who need the blacklisted file systems and therefore want to override 
the blacklisting can load the blacklisted module directly using `modprobe
$SOME_FS` in a terminal. This will call a script that offers to "un-blacklist"
the module for future use.

    # modprobe minix
    unblacklist: loading minix file system module
    unblacklist: Do you want to un-blacklist minix permanently (<y>es/<n>o/n<e>ver)? y
    unblacklist: minix un-blacklisted by creating /etc/modprobe.d/60-blacklist_fs-minix.conf

If the user selects **y**, the module is un-blacklisted by creating a symlink
to `/dev/null` (see above). Future attempts to mount minix file systems will
work with no issue, even after reboot, because the kernel's auto-loading
mechanism works for this file system again. If the user selects **n**, the
module remains blacklisted. If the user selects **e** or "never", the module
remains blacklisted, and on future **modprobe** attempts for this file system
the dialog above won't be shown any more.

Regardless of the user's answer, the module will be loaded for the time being;
i.e. subsequent **mount** commands for devices with this file system will succeed
until the module is unloaded or the system is rebooted.

For security reasons, it's recommended that you only un-blacklist file system
modules that you know you'll use on a regular basis, and just enable them
temporarily otherwise.


## Weak modules

This package contains the script `weak-modules2` which is necessary to make
3rd party kernel modules installed for one kernel available to
KABI-compatible kernels. SUSE ensures KABI compatibility over the life
time of a service pack in SUSE Enterprise Linux. See the
[SUSE SolidDriver Program](https://drivers.suse.com/doc/SolidDriver/) for
details.


## Kernel-specific sysctl settings

This package installs the file `50-kernel-uname_r.conf` which makes sure
that sysctl settings which are recommended for the currently running kernel
are applied by **systemd-sysctl.service** at boot time. These settings are
shipped in the file `/boot/sysctl.conf-$(uname -r)`, which is part of the
kernel package.
