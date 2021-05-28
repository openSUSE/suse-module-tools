#
# spec file for package suse-module-tools
#
# Copyright (c) 2021 SUSE LLC
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via https://bugs.opensuse.org/
#


# missing in SLE12
%{!?_rpmmacrodir: %global _rpmmacrodir %{_rpmconfigdir}/macros.d}
# missing in SLE15 (systemd-rpm-macros)
%{!?_modulesloaddir: %global _modulesloaddir /usr/lib/modules-load.d}

# Location for modprobe and depmod .conf files
#
# systemd-rpm-macros sets _modprobedir to /usr/lib/modprobe.d,
# but this has been supported by kmod only very recently.
# /lib/modprobe.d is safe, and will be transparently moved to
# /usr/lib/modprobe.d with the usr merge.
%global modprobe_dir /lib/modprobe.d
%global depmod_dir /lib/depmod.d

# List of legacy file systems to be blacklisted by default
%global fs_blacklist adfs affs bfs befs cramfs efs erofs exofs freevxfs hfs hpfs jfs minix nilfs2 ntfs omfs qnx4 qnx6 sysv ufs

# List of all files installed under modprobe.d
%global modprobe_conf_files 00-system 00-system-937216 10-unsupported-modules 50-blacklist 60-blacklist_fs-* 99-local
%global modprobe_conf_rpmsave %(echo "%{modprobe_conf_files}" | sed 's,\\([^ ]*\\),%{_sysconfdir}/modprobe.d/\\1.conf.rpmsave,g')

%if 0%{?sle_version} >= 120200 && 0%{?sle_version} < 150000
%global softdep_br_netfilter 1
%endif

Name:           suse-module-tools
Version:        16.0.1
Release:        0
Summary:        Configuration for module loading and SUSE-specific utilities for KMPs
License:        GPL-2.0-or-later
Group:          System/Base
URL:            https://github.com/openSUSE/suse-module-tools
Source0:        %{name}-%{version}.tar.xz
Source1:        %{name}.rpmlintrc
Requires:       /usr/bin/grep
Requires:       /usr/bin/gzip
Requires:       /usr/bin/sed
Requires:       coreutils
Requires:       findutils
Requires:       systemd-rpm-macros
Requires:       rpm
Requires(post): /usr/bin/grep
Requires(post): /usr/bin/sed
Requires(post): coreutils
# Use weak dependencies for dracut and kmod in order to
# keep Ring0 lean. In normal deployments, these packages
# will be available anyway.
Recommends:     dracut
Recommends:     kmod
# This release requires the dracut module 90nvdimm
Conflicts:      dracut < 49.1

%description
This package contains helper scripts for KMP installation and
uninstallation, as well as default configuration files for depmod and
modprobe. These utilities are provided by kmod-compat or
module-init-tools, whichever implementation you choose to install.


%prep
%setup -q

%build

%install
# now assemble the parts for modprobe.conf
cp modprobe.conf/modprobe.conf.common 00-system.conf
%ifarch ppc64le
ln -f modprobe.conf/modprobe.conf.ppc64 modprobe.conf/modprobe.conf.$RPM_ARCH
%endif
if [ -f "modprobe.conf/modprobe.conf.$RPM_ARCH" ]; then
	cat "modprobe.conf/modprobe.conf.$RPM_ARCH" >>00-system.conf
fi
install -d -m 755 "%{buildroot}%{modprobe_dir}"
install -d -m 755 "%{buildroot}%{_sysconfdir}/modprobe.d"
install -pm644 "10-unsupported-modules.conf" \
	"%{buildroot}%{modprobe_dir}/"
install -pm644 00-system.conf "%{buildroot}%{modprobe_dir}/"

%if 0%{?softdep_br_netfilter}
# softdep bridge->br_netfilter, SLE only
install -pm644 modprobe.conf/00-system-937216.conf %{buildroot}%{modprobe_dir}
%endif
%if 0%{?suse_version} >= 1550 || 0%{?sle_version} >= 150100
install -pm644 modprobe.conf/modprobe.conf.blacklist "%{buildroot}%{modprobe_dir}/50-blacklist.conf"
%endif
install -d -m 755 "%{buildroot}/%{depmod_dir}"
install -d -m 755 "%{buildroot}%{_sysconfdir}/depmod.d"
install -pm 644 "depmod-00-system.conf" "%{buildroot}%{depmod_dir}/00-system.conf"

# "/usr/lib/module-init-tools" name hardcoded in KMPs, mkinitrd, etc.
install -d -m 755 "%{buildroot}/usr/lib/module-init-tools"
install -pm 755 weak-modules2 "%{buildroot}/usr/lib/module-init-tools/"
install -pm 755 driver-check.sh "%{buildroot}/usr/lib/module-init-tools/"

%if 0%{?suse_version} < 1550
# rpm macros and helper
# The RPM Macros have been moved to the package rpm-config-SUSE after CODE15, thus are no longer
# shipped here
install -d -m 755 "%{buildroot}%{_rpmmacrodir}"
install -pm 644 "macros.initrd" "%{buildroot}%{_rpmmacrodir}"
%endif
install -pm 755 "regenerate-initrd-posttrans" "%{buildroot}/usr/lib/module-init-tools/"

install -d -m 755 "%{buildroot}%{_prefix}/bin"
install -pm 755 kmp-install "%{buildroot}%{_bindir}/"

# systemd service to load /boot/sysctl.conf-`uname -r`
install -d -m 755 "%{buildroot}%{_unitdir}/systemd-sysctl.service.d"
install -pm 644 50-kernel-uname_r.conf "%{buildroot}%{_unitdir}/systemd-sysctl.service.d"

# Ensure that the sg driver is loaded early (bsc#1036463)
# Not needed in SLE11, where sg is loaded via udev rule.
install -d -m 755 "%{buildroot}%{_modulesloaddir}"
install -pm 644 sg.conf "%{buildroot}%{_modulesloaddir}"
%ifarch ppc64 ppc64le
install -d -m 755 %{buildroot}/usr/lib/systemd/system-generators
install -m 755 udev-trigger-generator %{buildroot}/usr/lib/systemd/system-generators
%endif

mkdir -p %{buildroot}%{_defaultlicensedir}

%if 0%{?suse_version} >= 1550 || 0%{?sle_version} >= 150100
for mod in %{fs_blacklist}; do
    echo "\
# DO NOT EDIT THIS FILE! Copy to %{_sysconfdir}/modprobe.d and edit the copy.
#
# The $mod file system is blacklisted by default because it isn't actively
# supported by SUSE, not well maintained, or may have security vulnerabilites.
# To enable autoloading the $mod file system module, comment out the
# \"blacklist $mod\" statement below. ENABLE AT YOUR OWN RISK.
blacklist $mod" \
	>%{buildroot}%{modprobe_dir}/60-blacklist_fs-"$mod".conf
done
%endif

%post
%if 0%{?sle_version} < 150000
allowed=%{?is_opensuse:1}%{!?is_opensuse:0}
test_allow_on_install()
{
	# configure handling of unsupported modules
	# default is to allow them
	allow=1
	# don't change the setting during upgrade
	if test "$1" != 1; then
		allow=
		return
	fi
	# on SLES, the default is not to allow unsupported modules
	if grep -qs "Enterprise Server" %{_sysconfdir}/os-release; then
		allow=0
	else
		return
	fi
	# unless the admin passed "oem-modules=1" to the kernel during install
	if grep -qs '\<oem-modules=1\>' /proc/cmdline; then
		allow=1
		return
	fi
	# or if the installer already loaded some unsupported modules
	# (see TAINT_NO_SUPPORT in /etc/src/linux/include/linux/kernel.h)
	tainted=$(cat /proc/sys/kernel/tainted 2>/dev/null || echo 0)
	if test $((tainted & (1<<30))) != 0; then
		allow=1
		return
	fi
}
test_allow_on_install "$@"
if test -n "$allow" -a "$allow" != "$allowed"; then
	sed -ri 's/^( *allow_unsupported_modules *) [01]/\1 '"$allow"'/' \
		%{_sysconfdir}/modprobe.d/10-unsupported-modules.conf
fi
%endif

# Avoid systems becoming unbootable by blacklisting filesystem
# modules. Modules loaded at installation time will not be
# blacklisted (the blacklist statement is commented out).
# The modified file is written to /etc/modprobe.d
%if 0%{?suse_version} >= 1550 || 0%{?sle_version} >= 150100
for mod in %{fs_blacklist}; do
        inst=%{modprobe_dir}/60-blacklist_fs-"$mod".conf
	conf=%{_sysconfdir}/modprobe.d/60-blacklist_fs-"$mod".conf
	if [ -f "$inst" ] && \
	    sed '/^nodev/d;' /proc/filesystems | grep -q "\<$mod\>" && \
	    ( [ ! -f "$conf" ] || \
		  grep -q '^# __THIS FILE MAY BE MODIFIED__$' "$conf" )
	then
	    sed '
/^# DO NOT EDIT THIS FILE/d
/^blacklist '"$mod"'/{i\
# The next line was commented out by postinstall script of %{name}
s/^/# /
}
$a\
# Delete the following line to disallow modification of this file by rpm postinstall scripts.\
# __THIS FILE MAY BE MODIFIED__
' "$inst" >"$conf"
	fi
done
%endif

exit 0

%pre
# Avoid restoring old .rpmsave files in %posttrans
for f in %{modprobe_conf_rpmsave}; do
    if [ -f ${f} ]; then
	mv -f ${f} ${f}.%{name}
    fi
done
if [ -f %{_sysconfdir}/depmod.d/00-system.conf.rpmsave ]; then
    mv -f %{_sysconfdir}/depmod.d/00-system.conf.rpmsave \
          %{_sysconfdir}/depmod.d/00-system.conf.rpmsave.%{name}
fi
exit 0

%posttrans
# If the user had modified any of the configuration files installed under
# /etc, they'll now be renamed to .rpmsave files. Restore them.
for f in %{modprobe_conf_rpmsave}; do
    if [ -f ${f} ]; then
	mv -fv ${f} ${f%.rpmsave}
    fi
done
if [ -f %{_sysconfdir}/depmod.d/00-system.conf.rpmsave ]; then
    mv -fv %{_sysconfdir}/depmod.d/00-system.conf.rpmsave \
           %{_sysconfdir}/depmod.d/00-system.conf
fi
exit 0

%files
%defattr(-,root,root)

%if 0%{?sle_version:%{sle_version}}%{!?sle_version:150000} <= 120200
%dir %{_defaultlicensedir}
%endif
%license LICENSE
%doc README.SUSE
%{modprobe_dir}
%dir %{_sysconfdir}/modprobe.d
%{depmod_dir}
%dir %{_sysconfdir}/depmod.d
%if 0%{?suse_version} < 1550
%{_rpmmacrodir}/macros.initrd
%endif
%{_bindir}/kmp-install
/usr/lib/module-init-tools
%{_unitdir}/systemd-sysctl.service.d
%{_modulesloaddir}
%ifarch ppc64 ppc64le
/usr/lib/systemd/system-generators
%endif

%changelog
