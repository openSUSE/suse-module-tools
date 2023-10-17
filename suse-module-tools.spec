#
# spec file for package suse-module-tools
#
# Copyright (c) 2019 SUSE LINUX GmbH, Nuernberg, Germany.
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
Version:        12.13
Release:        0
Requires:       /sbin/depmod
Requires:       /sbin/mkinitrd
Requires:       findutils
Requires:       gzip
# for grepping /etc/SUSE-release
PreReq:         grep
# nm and rpmsort (rpm) are required by the weak-modules script which is invoked
# in post, it also requires getopt (coreutils) and sed
PreReq:         coreutils rpm
# XXX: this should be nm OR eu-nm, the script works with both
PreReq:         /usr/bin/eu-nm /bin/sed
Summary:        Configuration for module loading and SUSE-specific utilities for KMPs
License:        GPL-2.0-or-later
Group:          System/Base
Source:         README.SUSE
Source2:        modprobe.conf.tar.bz2
Source3:        depmod-00-system.conf
Source4:        10-unsupported-modules.conf
Source5:        weak-modules
Source6:        weak-modules2
Source7:        driver-check.sh
Source8:        suse-module-tools.rpmlintrc
Source9:        modsign-verify
Source10:       kmp-install
Source11:       macros.initrd
Source12:       regenerate-initrd-posttrans
Source13:       50-kernel-uname_r.conf
Source15:       LICENSE
Source16:       kernel-scriptlets.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
Provides:       suse-kernel-rpm-scriptlets = 0
# This release requires the dracut fix for bsc#1127891
# for the csiostor->cxgb4 softdep, but only on SLE12-SP4 and
# later, because there cxgb4 further dependencies.
%if 0%{?sle_version} >= 120400
Conflicts:      dracut < 44.2
%endif

%description
This package contains helper scripts for KMP installation and
uninstallation, as well as default configuration files for depmod and
modprobe. These utilities are provided by kmod-compat or
module-init-tools, whichever implementation you choose to install.

%prep
%setup -Tcqa2 -a 16
cp %{SOURCE15} .

%build

%install
b="%buildroot"
mkdir -p "$b/%_docdir/module-init-tools"
install -pm644 "%_sourcedir/README.SUSE" "$b/%_docdir/module-init-tools" 
#
# now assemble the parts for modprobe.conf
#
pushd modprobe.conf
cp modprobe.conf.common 00-system.conf
if [ -f "modprobe.conf.$RPM_ARCH" ]; then
	cat "modprobe.conf.$RPM_ARCH" >>00-system.conf
fi
install -d -m 755 "$b/etc/modprobe.d"
install -pm644 "%_sourcedir/10-unsupported-modules.conf" \
	"$b/etc/modprobe.d/"
install -pm644 00-system.conf "$b/etc/modprobe.d/"
install -pm644 modprobe.conf.local "$b/etc/modprobe.d/99-local.conf"
install -d -m 755 "$b/etc/depmod.d"
install -pm 644 "%_sourcedir/depmod-00-system.conf" \
	"$b/etc/depmod.d/00-system.conf"
popd

# "module-init-tools" name hardcoded in KMPs, mkinitrd, etc.
install -d -m 755 "$b/usr/lib/module-init-tools"
install -pm 755 %_sourcedir/weak-modules{,2} "$b/usr/lib/module-init-tools/"
install -pm 755 %_sourcedir/driver-check.sh "$b/usr/lib/module-init-tools/"

# rpm macros and helper
install -d -m 755 "$b/etc/rpm"
install -pm 644 "%_sourcedir/macros.initrd" "$b/etc/rpm/"
install -pm 755 "%_sourcedir/regenerate-initrd-posttrans" "$b/usr/lib/module-init-tools/"
install -d -m 755 "%{buildroot}/usr/lib/module-init-tools/kernel-scriptlets"
install -pm 755 "kernel-scriptlets/cert-script" "%{buildroot}/usr/lib/module-init-tools/kernel-scriptlets"
install -pm 755 "kernel-scriptlets/inkmp-script" "%{buildroot}/usr/lib/module-init-tools/kernel-scriptlets"
install -pm 755 "kernel-scriptlets/kmp-script" "%{buildroot}/usr/lib/module-init-tools/kernel-scriptlets"
install -pm 755 "kernel-scriptlets/rpm-script" "%{buildroot}/usr/lib/module-init-tools/kernel-scriptlets"
for i in "pre" "preun" "post" "posttrans" "postun" ; do
    ln -s cert-script %{buildroot}/usr/lib/module-init-tools/kernel-scriptlets/cert-$i
    ln -s inkmp-script %{buildroot}/usr/lib/module-init-tools/kernel-scriptlets/inkmp-$i
    ln -s kmp-script %{buildroot}/usr/lib/module-init-tools/kernel-scriptlets/kmp-$i
    ln -s rpm-script %{buildroot}/usr/lib/module-init-tools/kernel-scriptlets/rpm-$i
done

# modsign-verify for verifying module signatures
install -d -m 755 "$b/usr/bin"
install -pm 755 %_sourcedir/modsign-verify "$b/usr/bin/"
install -pm 755 %_sourcedir/kmp-install "$b/usr/bin/"

# systemd service to load /boot/sysctl.conf-`uname -r`
install -d -m 755 "$b/usr/lib/systemd/system/systemd-sysctl.service.d"
install -pm 644 %_sourcedir/50-kernel-uname_r.conf "$b/usr/lib/systemd/system/systemd-sysctl.service.d"

%post
test_allow_on_install()
{
	# configure handling of unsupported modules
	# default is to allow them
	allow=1
	# if the obsolete LOAD_UNSUPPORTED_MODULES_AUTOMATICALLY variable is
	# set to no, don't allow (this was used in SLES 9 and 10)
	if test -e /etc/sysconfig/hardware/config; then
		. /etc/sysconfig/hardware/config
		if test "x$LOAD_UNSUPPORTED_MODULES_AUTOMATICALLY" = "xno"; then
			allow=0
		fi
		# obsolete
		rm /etc/sysconfig/hardware/config
	fi
	# don't change the setting during upgrade
	if test "$1" != 1; then
		return
	fi
	# on SLES, the default is not to allow unsupported modules
	if grep -qs "Enterprise Server" /etc/SuSE-release; then
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
	# (see TAINT_NO_SUPPORT in /usr/src/linux/include/linux/kernel.h)
	tainted=$(cat /proc/sys/kernel/tainted 2>/dev/null || echo 0)
	if test $((tainted & (1<<30))) != 0; then
		allow=1
		return
	fi
}
# upgrade from old locations
if test -e /etc/modprobe.d/unsupported-modules; then
	mv -f /etc/modprobe.d/unsupported-modules \
		/etc/modprobe.d/10-unsupported-modules.conf
fi
if test -e /etc/modprobe.conf.local; then
	mv -f /etc/modprobe.conf.local \
		/etc/modprobe.d/99-local.conf
fi
test_allow_on_install "$@"
if test "$allow" = "0"; then
	sed -ri 's/^( *allow_unsupported_modules *) 1/\1 0/' \
		/etc/modprobe.d/10-unsupported-modules.conf
fi

%files
%defattr(-,root,root)
%dir               /etc/modprobe.d
%config            /etc/modprobe.d/00-system.conf
%config(noreplace) /etc/modprobe.d/10-unsupported-modules.conf
%config(noreplace) /etc/modprobe.d/99-local.conf
%dir               /etc/depmod.d
%config            /etc/depmod.d/00-system.conf
%config /etc/rpm/macros.initrd
%_docdir/module-init-tools
%license LICENSE
/usr/bin/kmp-install
/usr/bin/modsign-verify
/usr/lib/module-init-tools
/usr/lib/systemd/system/systemd-sysctl.service.d

%changelog
