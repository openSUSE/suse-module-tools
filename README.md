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

Blacklisting is accomplished by placing configuration files called
`60-blacklist_fs-$SOME_FS.conf` under `/lib/modprobe.d`. The current list 
of blacklisted filesystems is:

    @FS_BLACKLIST@

### CAVEAT

In the very unlikely case that one of the blacklisted file systems is necessary
for your system to boot, make sure you un-blacklist your file system before
rebooting (see below). 

### Un-blacklisting a file system

Users that need one of the blacklisted file systems may want to un-blacklist
them. 

If a user tries to **mount(8)** a device with an unsupported file system, the
mount command prints "`unsupported file system type 'SOME_FS'`". **mount(8)**
can't distinguish between a really unsupported file system (kernel module
non-existent) and a blacklisted file system.

Users who need the blacklisted file systems and therefore want to override 
the blacklisting can load the blacklisted module directly:

    modprobe -v somefs

This will call a script that offers to "un-blacklist" the module for future
use. The module will be loaded whether or not the user opts to un-blacklist
it.


## Weak modules

This package contains the script `weak-modules2` which is necessary to make
3rd party kernel modules installed for one kernel available to 
KABI-compatible kernels. SUSE ensures KABI compatibility over the life
time of a service pack in SUSE Enterprise Linux. See the 
[SUSE SolidDriver Program](https://drivers.suse.com/doc/SolidDriver/) for
details.
