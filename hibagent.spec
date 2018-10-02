Name:           hibagent
Version:        1.0.0
Release:        1%{?dist}
Summary:        Hibernation trigger utility for AWS EC2

Group:          Development/Languages
License:        ASL 2.0
URL:            https://github.com/awslabs/hibagent
Source0:        hibagent-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  system-python system-python-devel
Requires(preun): initscripts
Requires(postun): initscripts
Requires(post): initscripts
Requires: /sbin/service
Requires: /sbin/chkconfig

%description
An EC2 agent that watches for instance stop notifications and initiates hibernation

%prep
%setup -q -n hibagent-%{version}

%build
%{__sys_python} setup.py build

%install
%{__sys_python} setup.py install --prefix=usr -O1 --skip-build --root $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%doc LICENSE.txt README.md
%{_sysconfdir}/hibagent-config.cfg
%{_sysconfdir}/init.d/hibagent
%{_bindir}/hibagent
%{_bindir}/enable-ec2-spot-hibernation
%{sys_python_sitelib}/*

%clean
rm -rf $RPM_BUILD_ROOT

%post
if [ $1 = 1 ]; then
    #initial installation
    /sbin/chkconfig --add hibagent
fi

%preun
if [ $1 = 0 ]; then
    # Package removal, not upgrade
    /sbin/service hibagent stop >/dev/null 2>&1
    /sbin/chkconfig --del hibagent
fi

%postun
if [ $1 -ge 1 ]; then
    /sbin/service hibagent condrestart >/dev/null 2>&1 || :
fi

%changelog
* Mon Sep 4 2017 Aleksei Besogonov <cyberax@amazon.com> - 1.0.0-1
- Initial build
