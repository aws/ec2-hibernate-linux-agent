Name:           hibagent
Version:        1.0.0
Release:        1%{?dist}
Summary:        Hibernation trigger utility for AWS EC2

Group:          Development/Languages
License:        MIT
URL:            https://github.com/awslabs/hibagent
Source0:        https://github.com/awslabs/hibagent-%{version}.tar.gz
Requires:       python27
BuildArch:      noarch

%description
hibagent provides a simple agent to trigger instance hibernation upon receiving
a signal from EC2.

%prep
%setup -q -n hibagent-%{version}

%build
%{__python27} setup.py build

%install
%{__python27} setup.py install --prefix=usr -O1 --skip-build --root $RPM_BUILD_ROOT --record=INSTALLED_FILES

%files -f INSTALLED_FILES
%defattr(-,root,root)

%doc LICENSE.txt README.md

%clean
rm -rf $RPM_BUILD_ROOT

%changelog
* Mon Sep 4 2017 Aleksei Besogonov <cyberax@amazon.com> - 1.0.0-1
- Initial build
