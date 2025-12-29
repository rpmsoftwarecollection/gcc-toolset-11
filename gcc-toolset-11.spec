%global __python /usr/bin/python3
%global scl gcc-toolset-11
%scl_package %scl

Summary: Package that installs %scl
Name: %scl_name
Version: 11.1
Release: 3%{?dist}
License: GPLv2+
Group: Applications/File
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Source0: README
Source1: sudo.sh

# The base package requires just the toolchain and the perftools.
Requires: %{scl_prefix}toolchain %{scl_prefix}perftools
Obsoletes: %{name} < %{version}-%{release}
Obsoletes: %{scl_prefix}dockerfiles < %{version}-%{release}

BuildRequires: scl-utils-build >= 20120927-11
BuildRequires: iso-codes
BuildRequires: help2man
%if 0%{?rhel} >= 8
BuildRequires: python3-devel
%endif

%description
This is the main package for %scl Software Collection.

%package runtime
Summary: Package that handles %scl Software Collection.
Group: Applications/File
Requires: scl-utils >= 20120927-11
Obsoletes: %{name}-runtime < %{version}-%{release}
%if 0%{?rhel} >= 7
Requires(post): %{_root_sbindir}/semanage %{_root_sbindir}/restorecon
Requires(postun): %{_root_sbindir}/semanage %{_root_sbindir}/restorecon
%else
Requires(post): libselinux policycoreutils-python-utils
Requires(postun): libselinux policycoreutils-python-utils
%endif

%description runtime
Package shipping essential scripts to work with %scl Software Collection.

%package build
Summary: Package shipping basic build configuration
Group: Applications/File
Requires: %{scl_prefix}runtime
Requires: scl-utils-build >= 20120927-11
Obsoletes: %{name}-build < %{version}-%{release}

%description build
Package shipping essential configuration macros to build %scl Software Collection.

%package toolchain
Summary: Package shipping basic toolchain applications
Group: Applications/File
Requires: %{scl_prefix}runtime
Requires: %{scl_prefix}gcc %{scl_prefix}gcc-c++ %{scl_prefix}gcc-gfortran
Requires: %{scl_prefix}binutils %{scl_prefix}gdb %{scl_prefix}strace
Requires: %{scl_prefix}dwz %{scl_prefix}elfutils
Requires: %{scl_prefix}ltrace %{scl_prefix}make
Requires: %{scl_prefix}annobin
%if 0%{?rhel} <= 7
Requires: %{scl_prefix}memstomp
%endif
Obsoletes: %{name}-toolchain < %{version}-%{release}

%description toolchain
Package shipping basic toolchain applications (compiler, debugger, ...)

%package perftools
Summary: Package shipping performance tools
Group: Applications/File
Requires: %{scl_prefix}runtime
Requires: %{scl_prefix}systemtap %{scl_prefix}valgrind
%if 0%{?rhel} <= 7
Requires: %{scl_prefix}oprofile
%ifarch x86_64
Requires: %{scl_prefix}dyninst
%endif
%else
%ifarch x86_64 ppc64le aarch64
Requires: %{scl_prefix}dyninst
%endif
%endif
Obsoletes: %{name}-perftools < %{version}-%{release}

%description perftools
%if 0%{?rhel} <= 7
Package shipping performance tools (systemtap, oprofile)
%else
Package shipping performance tools (systemtap)
%endif

%prep
%setup -c -T

# This section generates README file from a template and creates man page
# from that file, expanding RPM macros in the template file.
cat <<'EOF' | tee README
%{expand:%(cat %{SOURCE0})}
EOF

%build

# Temporary helper script used by help2man.
cat <<\EOF | tee h2m_helper
#!/bin/sh
if [ "$1" = "--version" ]; then
  printf '%%s' "%{?scl_name} %{version} Software Collection"
else
  cat README
fi
EOF
chmod a+x h2m_helper
# Generate the man page.
help2man -N --section 7 ./h2m_helper -o %{?scl_name}.7

# Enable collection script
# ========================
cat <<EOF >enable
# General environment variables
export PATH=%{_bindir}\${PATH:+:\${PATH}}
export MANPATH=%{_mandir}\${MANPATH:+:\${MANPATH}}
export INFOPATH=%{_infodir}\${INFOPATH:+:\${INFOPATH}}
export PCP_DIR=%{_scl_root}
export CC=%{_bindir}/gcc
export CXX=%{_bindir}/g++
# bz847911 workaround:
# we need to evaluate rpm's installed run-time % { _libdir }, not rpmbuild time
# or else /etc/ld.so.conf.d files?
rpmlibdir=\$(rpm --eval "%%{_libdir}")
# bz1017604: On 64-bit hosts, we should include also the 32-bit library path.
# bz1873882: On 32-bit hosts, we should include also the 64-bit library path.
# bz2027377: Avoid unbound variables
if [ "\$rpmlibdir" != "\${rpmlibdir/lib64/}" ]; then
  rpmlibdir32=":%{_scl_root}\${rpmlibdir/lib64/lib}"
  dynpath32="\$rpmlibdir32/dyninst"
  rpmlibdir64=
  dynpath64=
else
  rpmlibdir64=":%{_scl_root}\${rpmlibdir/lib/lib64}"
  dynpath64="\$rpmlibdir64/dyninst"
  rpmlibdir32=
  dynpath32=
fi
# Add SCL dyninst to LD_LIBRARY_PATH, both 64- and 32-bit paths.
export LD_LIBRARY_PATH=%{_scl_root}\$rpmlibdir/dyninst\$dynpath64\$dynpath32\${LD_LIBRARY_PATH:+:\${LD_LIBRARY_PATH}}
# Now prepend the usual /opt/.../usr/lib{64,}.
export LD_LIBRARY_PATH=%{_scl_root}\$rpmlibdir\$rpmlibdir64\$rpmlibdir32\${LD_LIBRARY_PATH:+:\${LD_LIBRARY_PATH}}
export PKG_CONFIG_PATH=%{_libdir}/pkgconfig\${PKG_CONFIG_PATH:+:\${PKG_CONFIG_PATH}}
EOF

# Sudo script
# ===========
cat <<'EOF' > sudo
%{expand:%(cat %{SOURCE1})}
EOF

%install
(%{scl_install})

# This allows users to build packages using DTS/GTS.
cat >> %{buildroot}%{_root_sysconfdir}/rpm/macros.%{scl}-config << EOF
%%enable_devtoolset11 %%global ___build_pre %%{___build_pre}; source scl_source enable %{scl} || :
EOF

mkdir -p %{buildroot}%{_scl_root}/etc/alternatives %{buildroot}%{_scl_root}/var/lib/alternatives

install -d -m 755 %{buildroot}%{_scl_scripts}
install -p -m 755 enable %{buildroot}%{_scl_scripts}/

install -d -m 755 %{buildroot}%{_scl_scripts}
install -p -m 755 sudo %{buildroot}%{_bindir}/

# Other directories that should be owned by the runtime
install -d -m 755 %{buildroot}%{_datadir}/appdata
# Otherwise unowned perl directories
install -d -m 755 %{buildroot}%{_libdir}/perl5
install -d -m 755 %{buildroot}%{_libdir}/perl5/vendor_perl
install -d -m 755 %{buildroot}%{_libdir}/perl5/vendor_perl/auto

# Install generated man page.
install -d -m 755 %{buildroot}%{_mandir}/man7
install -p -m 644 %{?scl_name}.7 %{buildroot}%{_mandir}/man7/

%files
%doc README
%{_mandir}/man7/%{?scl_name}.*

%files runtime
%scl_files
%attr(0644,root,root) %verify(not md5 size mtime) %ghost %config(missingok,noreplace) %{_sysconfdir}/selinux-equiv.created
%dir %{_scl_root}/etc/alternatives
%dir %{_datadir}/appdata

%files build
%{_root_sysconfdir}/rpm/macros.%{scl}*

%files toolchain

%files perftools

%post runtime
if [ ! -f %{_sysconfdir}/selinux-equiv.created ]; then
  /usr/sbin/semanage fcontext -a -e / %{_scl_root}
  restorecon -R %{_scl_root}
  touch %{_sysconfdir}/selinux-equiv.created
fi

%preun runtime
[ $1 = 0 ] && rm -f %{_sysconfdir}/selinux-equiv.created || :

%postun runtime
if [ $1 = 0 ]; then
  /usr/sbin/semanage fcontext -d %{_scl_root}
  [ -d %{_scl_root} ] && restorecon -R %{_scl_root} || :
fi

%changelog
* Fri Dec 17 2021 Marek Polacek <polacek@redhat.com> - 11.1-1
- fix unbound variables in 'MANPATH' (#2027377)

* Mon Nov 29 2021 Marek Polacek <polacek@redhat.com> - 11.1-0
- fix unbound variables in 'enable' (#2027377)

* Wed Jul 28 2021 Marek Polacek <polacek@redhat.com> - 11.0-1
- on 32-bit hosts, include also the 64-bit library path (#1986097)

* Wed Apr 21 2021 Marek Polacek <polacek@redhat.com> - 11.0-0
- new package
