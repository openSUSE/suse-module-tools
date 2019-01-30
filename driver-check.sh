#!/bin/bash

VERSION="0.5"
MAINTAINER="Michal Marek <mmarek@suse.cz>"
USAGE="Usage: ${0##*/} [-o|--out output-file]"

errors=0
warnings=0

trap 'rm -rf "$tmp"' EXIT
tmp=$(mktemp -d)

rpm()
{
	# rpm tends to send localized error messages to stdout :-(
	LC_ALL=C command rpm "$@"
}

file_owner()
{
	local f=$1

	if (cd "$tmp/rpms"; grep -lFx "$f" *); then
		return
	fi
	rpm -qf "$f"
}

_explain_called=()
explain()
{
	local caller=${BASH_LINENO[0]}

	if test -n "${_explain_called[$caller]}"; then
		return
	fi
	_explain_called[$caller]=1
	echo "$*"
}

error()
{
	echo "ERROR: $*"
	let errors++
}

warning()
{
	echo "warning: $*" >&2
	let warnings++
}

check_system()
{
	if test ! -x /usr/lib/module-init-tools/weak-modules2; then
		echo "This tool only works on SLE11 and later systems" >&2
		exit 1
	fi
	if ! zypper search >/dev/null; then
		echo "Cannot run zypper, please correct the above problem" >&2
		exit 1
	fi
}

check_rpm_V()
{
	local attrs flags path

	# kernel packages contain the initrd with permissions 0644,
	# but dracut creates initrd with 0600. That's not an error.
	while read attrs flags path; do
	        case $attrs in
		.M.......)
			if [[ "${path#/boot/initrd}" != "$path" && \
				      -f "$path" && \
				       $(stat -c %a "$path") = 600 ]]; then
				    continue
			fi
			;;
		esac
		echo "$attrs $flags $path"
		error "$rpm was not installed correctly (see above)"
	done
}

check_rpm()
{
	local rpm=$1 name=${1%-*-*} out

	# ignore changes to %config and %doc files and ignore changed mtimes
	check_rpm_V < <(rpm -V "$rpm" | grep -Ev '^[^ ]{8,}  [cd] |^\.{7}T\.* ')
}

check_kernel_package()
{
	local kernel=$1

	if ! rpm -q --qf '%{description}\n' "$kernel" | grep -q '^GIT '; then
		error "$kernel does not look like a SUSE kernel package (no commit id)"
	fi
	if ! rpm -q --qf '%{postin}\n' "$kernel" | grep -q 'weak-modules2'; then
		error "$kernel does not look like a SUSE kernel package (wrong %post script)"
	fi
}

check_krel()
{
	local krel=$1 system_map module_symvers msg res args bad=false
	local mit_version

	system_map="/boot/System.map-$krel"
	module_symvers="/boot/symvers-$krel.gz"
	if ! test -e "$system_map"; then
		error "$system_map not found"
		bad=true
	fi
	if ! test -e "$module_symvers"; then
		error "$module_symvers not found"
		bad=true
	fi
	if $bad; then
		explain "Each kernel must install /boot/System.map-\$version and /boot/symvers-\$version.gz to be able to check module dependencies."
		return
	fi
	set -- $(/sbin/depmod --version | sed -rn 's/.* ([0-9]+)\.([0-9]+)(\..*)?/\1 \2/p')
	if test -n "$1" -a -n "$2"; then
		let "mit_version = $1 * 100 + $2"
	else
		warning "Cannot determine module-init-tools version, this is a bug in the script"
		mit_version=0
	fi
	# depmod -E was introduced in 3.10
	if test "$mit_version" -ge 310; then
		gzip -cd <"$module_symvers" >"$tmp/symvers"
		args=(-E "$tmp/symvers")
	else
		args=(-F "$system_map")
	fi
	msg=$(/sbin/depmod -n -e "${args[@]}" "$krel" 2>&1 >/dev/null)
	res=$?
	if test -n "$msg" -o "$res" -ne 0; then
		echo "$msg"
		error "depmod $krel returned errors (exit code $res)"
		explain "depmod must pass without errors otherwise KMP scripts will break"
	fi

}

req_re='^(kernel\([^:]*:kernel[[:alnum:]_]*\)|ksym\([^:]*:(struct_module|module_layout)\)) = [0-9a-f]+'
check_kmp()
{
	local kmp=$1 prefix prev_krel krel path found_module=false

	if ! rpm -q --qf '%{postin}\n' "$kmp" | grep -q 'weak-modules2'; then
		error "$kmp does not look like a SUSE kernel module package (wrong %post)"
	fi
	if ! rpm -q -R "$kmp" | grep -Eq "$req_re"; then
		error "$kmp does not have proper dependencies"
	fi
	exec 3< <(sed -rn 's:^(/lib/modules)?/([^/]*)/(.*\.ko)$:\1 \2 \3:p' \
		"$tmp/rpms/$kmp")
	while read prefix krel path <&3; do
		found_module=true
		if test "$prefix" != "/lib/modules"; then
			error "$kmp installs modules outside of /lib/modules"
			continue
		fi
		if test -z "$prev_krel"; then
			prev_krel=$krel
		elif test "$prev_krel" != "$krel"; then
			error "$kmp installs modules for multiple kernel versions"
		fi
		case "$path" in
		updates/* | extra/*)
			;;
		weak-updates/*)
			error "$kmp installs modules in weak-updates/ instead of updates/ or extra/"
			explain "The weak-modules directory is reserved for automatically generated symlinks"
			;;
		*)
			error "$kmp installs modules in an invalid directory"
			explain \
"KMPs must install modules in the updates/ or extra/ subdirectories for the
weak-modules2 script to work"
			;;
		esac

	done
	if ! $found_module; then
		error "$kmp does not contain any modules"
		explain \
"A KMP must contain it's modules in the rpm filelist, otherwise weak-modules2
will not work"
	fi
}

check_ko()
{
	local ko=$1 kmp bad=false

	case "$ko" in
	*/weak-updates/*)
		if test -L "$ko"; then
			return
		fi
	esac
	kmp=$(file_owner "$ko")
	case "$kmp" in
	kernel-* | *-kmp-*) ;;
	*not\ owned\ by\ any\ package)
		error "$ko is not owned by any package"
		bad=true
		;;
	*)
		error "$ko is not packaged as a KMP"
		bad=true
		;;
	esac
	if $bad; then
		explain \
"External kernel modules must be packaged as KMPs, see
http://developer.novell.com/wiki/index.php/Kernel_Module_Packages_Manuals"
	fi
}

options=$(getopt -n "${0##*/}" -o o:h --long out:,help -- "$@")
if test "$?" -ne 0; then
	echo "$USAGE" >&2
	exit 1
fi
eval set -- "$options"
logfile="driver-check-report.txt"
while :; do
	case "$1" in
	-o | --out)
		logfile="$2"
		shift 2
		;;
	-h | --help)
		echo "${0##*/} $VERSION"
		echo "$USAGE"
		echo
		echo "Please report bugs and enhancement requests to $MAINTAINER"
		exit 0
		;;
	--)
		shift
		break
		;;
	esac
done
if test $# -gt 0; then
	echo "Unrecognized arguments: $*" >&2
	echo "$USAGE" >&2
	exit 1
fi

check_system

# set up redirection
if test $logfile != "-"; then
	if test -e "$logfile"; then
		mv -f "$logfile" "$logfile~"
	fi
	if test -e /proc/self; then
		exec 99> >(cat >"$logfile")
		exec 1>&99
		exec 2> >(tee -a /proc/self/fd/99 >&2)
	else
		exec 1>"$logfile"
		exec 2>"$logfile"
		warning "/proc not mounted"
	fi
fi
echo "${0##*/} $VERSION started at $(date -R)" >&2

smt=$(rpm -q --qf '%{n}-%{v}-%{r}\n' module-init-tools) || \
    smt=$(rpm -q --qf '%{n}-%{v}-%{r}\n' suse-module-tools)
check_rpm "$smt"

mkdir -p "$tmp/rpms"
found_kernel=false
for rpm in $(rpm -qa --qf '%{n}-%{v}-%{r}\n' 'kernel-*' '*-kmp-*' | \
		/usr/lib/rpm/rpmsort); do
	case "$rpm" in
	kernel-source-* | kernel-syms-* | kernel-*-debug* | kernel-*-man-* | \
	kernel-*-devel-* | kernel-firmware-* | kernel-coverage-* | \
	kernel-docs-* | kernel-devel-*)
		continue
	esac
	# store the filelist to speed up file_owner()
	rpm -ql "$rpm" >"$tmp/rpms/$rpm"
	check_rpm "$rpm"
	case "$rpm" in
	kernel-*)
		check_kernel_package "$rpm"
		found_kernel=true
		;;
	*-kmp-*)
		check_kmp "$rpm"
		;;
	esac
done
if ! $found_kernel; then
	warning "no kernel package found"
fi

for krel in /lib/modules/*/kernel; do
	krel=${krel%/kernel}
	krel=${krel##*/}
	check_krel "$krel"
done

modules=($(find /lib/modules/ -name '*.ko'))
for module in "${modules[@]}"; do
	check_ko "$module"
done

echo "Found $errors error(s) and $warnings warning(s)" >&2
if test "$logfile" != -; then
	echo "Report written to $logfile at $(date -R)" >&2
else
	echo "Report finished at $(date -R)" >&2
fi
if test $errors -eq 0; then
	exit 0
else
	exit 1
fi
