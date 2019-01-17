#
# spec file for package suse-module-tools
#
# Copyright (c) 2018 SUSE LINUX GmbH, Nuernberg, Germany.
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


Name:           suse-module-tools
Version:        15.0.10
Release:        0
Summary:        Configuration for module loading and SUSE-specific utilities for KMPs
License:        GPL-2.0-or-later
Group:          System/Base
Url:            https://github.com/openSUSE/suse-module-tools
Source0:        %{name}-%{version}.tar.xz
Source1:        %{name}.rpmlintrc
# not /sbin/mkinitrd because base distros don't provide it on purpose
Requires:       coreutils
Requires:       findutils
Requires:       grep
Requires:       gzip
Requires:       mkinitrd
# module-init-tools in older distros, kmod-compat in later ones
Requires:       /sbin/depmod
Requires:       rpm
Requires:       sed

%description
This package contains helper scripts for KMP installation and
uninstallation, as well as default configuration files for depmod and
modprobe. These utilities are provided by kmod-compat or
module-init-tools, whichever implementation you choose to install.


%package legacy
Summary:        Legacy "weak-modules" script for Code10
Group:          System/Base
Requires:       %{name}
Requires:       binutils

%description legacy
This package contains the legacy "weak-modules" script for kernel
module package (KMP) support. It was replaced by "weak-modules2" in
SLE 11 and later.

%prep
%setup -q

%build
%if 0%{?is_opensuse} == 0
sed -ri 's/^( *allow_unsupported_modules *) 1/\1 0/' \
	10-unsupported-modules.conf
%endif

%install
# now assemble the parts for modprobe.conf
cp modprobe.conf/modprobe.conf.common 00-system.conf
if [ -f "modprobe.conf/modprobe.conf.$RPM_ARCH" ]; then
	cat "modprobe.conf/modprobe.conf.$RPM_ARCH" >>00-system.conf
fi
install -d -m 755 "%{buildroot}%{_sysconfdir}/modprobe.d"
install -pm644 "10-unsupported-modules.conf" \
	"%{buildroot}%{_sysconfdir}/modprobe.d/"
install -pm644 00-system.conf "%{buildroot}%{_sysconfdir}/modprobe.d/"
install -pm644 modprobe.conf/modprobe.conf.blacklist "%{buildroot}%{_sysconfdir}/modprobe.d/50-blacklist.conf"
install -pm644 modprobe.conf/modprobe.conf.local "%{buildroot}%{_sysconfdir}/modprobe.d/99-local.conf"
install -d -m 755 "%{buildroot}%{_sysconfdir}/depmod.d"
install -pm 644 "depmod-00-system.conf" \
	"%{buildroot}%{_sysconfdir}/depmod.d/00-system.conf"

# "module-init-tools" name hardcoded in KMPs, mkinitrd, etc.
install -d -m 755 "%{buildroot}%{_libexecdir}/module-init-tools"
install -pm 755 weak-modules{,2} "%{buildroot}%{_libexecdir}/module-init-tools/"
install -pm 755 driver-check.sh "%{buildroot}%{_libexecdir}/module-init-tools/"

# rpm macros and helper
install -d -m 755 "%{buildroot}%{_sysconfdir}/rpm"
install -pm 644 "macros.initrd" "%{buildroot}%{_sysconfdir}/rpm/"
install -pm 755 "regenerate-initrd-posttrans" "%{buildroot}%{_libexecdir}/module-init-tools/"

install -d -m 755 "%{buildroot}%{_prefix}/bin"
install -pm 755 kmp-install "%{buildroot}%{_bindir}/"
# modhash for calculating hash of signed kernel module
install -pm 755 modhash "%{buildroot}%{_bindir}/"

# systemd service to load /boot/sysctl.conf-`uname -r`
install -d -m 755 "%{buildroot}%{_libexecdir}/systemd/system/systemd-sysctl.service.d"
install -pm 644 50-kernel-uname_r.conf "%{buildroot}%{_libexecdir}/systemd/system/systemd-sysctl.service.d"

# Ensure that the sg driver is loaded early (bsc#1036463)
# Not needed in SLE11, where sg is loaded via udev rule.
install -d -m 755 "%{buildroot}%{_sysconfdir}/modules-load.d"
install -pm 644 sg.conf "%{buildroot}%{_sysconfdir}/modules-load.d"

mkdir -p %{buildroot}%{_defaultlicensedir}

%post
%if 0%{?sle_version} >= 150000
# Delete obsolete unsupported-modules file from SLE11
rm -f %{_sysconfdir}/modprobe.d/unsupported-modules
%else
# Logic for releases below CODE 15
%if 0%{?is_opensuse} == 1
allowed=1
%else
allowed=0
%endif
test_allow_on_install()
{
	# configure handling of unsupported modules
	# default is to allow them
	allow=1
	# if the obsolete LOAD_UNSUPPORTED_MODULES_AUTOMATICALLY variable is
	# set to no, don't allow (this was used in SLES 9 and 10)
	if test -e %{_sysconfdir}/sysconfig/hardware/config; then
		. %{_sysconfdir}/sysconfig/hardware/config
		if test "x$LOAD_UNSUPPORTED_MODULES_AUTOMATICALLY" = "xno"; then
			allow=0
		fi
		# obsolete
		rm %{_sysconfdir}/sysconfig/hardware/config
	fi
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
# upgrade from old locations
if test -e %{_sysconfdir}/modprobe.d/unsupported-modules; then
	mv -f %{_sysconfdir}/modprobe.d/unsupported-modules \
		%{_sysconfdir}/modprobe.d/10-unsupported-modules.conf
fi
test_allow_on_install "$@"
if test -n "$allow" -a "$allow" != "$allowed"; then
	sed -ri 's/^( *allow_unsupported_modules *) [01]/\1 '"$allow"'/' \
		%{_sysconfdir}/modprobe.d/10-unsupported-modules.conf
fi
%endif

# upgrade from old locations
if test -e %{_sysconfdir}/modprobe.conf.local; then
	mv -f %{_sysconfdir}/modprobe.conf.local \
		%{_sysconfdir}/modprobe.d/99-local.conf
fi

%files
%defattr(-,root,root)

%if 0%{?sle_version:%{sle_version}}%{!?sle_version:150000} <= 120200
%dir %{_defaultlicensedir}
%endif
%license LICENSE
%doc README.SUSE
%dir %{_sysconfdir}/modprobe.d
%config %{_sysconfdir}/modprobe.d/00-system.conf
%config(noreplace) %{_sysconfdir}/modprobe.d/10-unsupported-modules.conf
%config(noreplace) %{_sysconfdir}/modprobe.d/50-blacklist.conf
%config(noreplace) %{_sysconfdir}/modprobe.d/99-local.conf
%dir %{_sysconfdir}/depmod.d
%config %{_sysconfdir}/depmod.d/00-system.conf
%config %{_sysconfdir}/rpm/macros.initrd
%{_bindir}/modhash
%{_bindir}/kmp-install
%{_libexecdir}/module-init-tools
%exclude %{_libexecdir}/module-init-tools/weak-modules
%{_libexecdir}/systemd/system/systemd-sysctl.service.d
%dir %{_sysconfdir}/modules-load.d
%config(noreplace) %{_sysconfdir}/modules-load.d/sg.conf

%files legacy
%defattr(-,root,root)

%{_libexecdir}/module-init-tools/weak-modules

%changelog
