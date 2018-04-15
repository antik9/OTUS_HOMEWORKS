License:        BSD
Vendor:         Otus
Group:          PD01
URL:            http://otus.ru/lessons/3/
Source0:        otus-%{current_datetime}.tar.gz
BuildRoot:      %{_tmppath}/otus-%{current_datetime}
Name:           ip2w
Version:        0.0.1
Release:        1
BuildArch:      noarch
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
BuildRequires: systemd
Requires:       python3.6 uwsgi nginx
Summary:        The ip to weather centos deamon

%description
The daemon respond to GET requests with json-formatted weather info

Git version: %{git_version} (branch: %{git_branch})

%define __etcdir    /usr/local/etc
%define __logdir    /val/log/
%define __bindir    /usr/local/ip2w/
%define __systemddir    /usr/lib/systemd/system/
%define __pathwithsource        /home/HW_06_api/

%prep

%install
[ "%{buildroot}" != "/" ] && rm -fr %{buildroot}
%{__mkdir} -p %{buildroot}/%{__systemddir}
%{__mkdir} -p %{buildroot}/%{__etcdir}
%{__mkdir} -p %{buildroot}/%{__bindir}
%{__mkdir} -p %{buildroot}/%{__logdir}


%{__install} -pD -m 644 %{__pathwithsource}/server/%{name}.py %{buildroot}/%{__bindir}/%{name}.py
%{__install} -pD -m 644 %{__pathwithsource}/server/%{name}.ini %{buildroot}/%{__etcdir}/%{name}.ini
%{__install} -pD -m 644 %{__pathwithsource}/%{name}.service %{buildroot}/%{__systemddir}/%{name}.service

%post
%systemd_post %{name}.service
systemctl daemon-reload

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun %{name}.service

%clean
[ "%{buildroot}" != "/" ] && rm -fr %{buildroot}


%files
%{__logdir}
%{__bindir}
%{__systemddir}
%{__etcdir}

