Name:		clamav
Summary:	ClamAV for QMail Toaster
Version:	0.98
Release:	0%{?dist}
License:	GPL
Group:		System Enviroment/Daemons
URL:		http://www.clamav.net
Source0:	http://downloads.sourceforge.net/clamav/%{name}-%{version}.tar.gz
Source1:	freshclam.logrotate
Source2:	freshclam.init
Source3:	clamav.run.supervise
Source4:	clamav.run.log.supervise
Patch0:		clamav-0.9x-qmailtoaster.patch
BuildRequires:	autoconf
BuildRequires:	automake
BuildRequires:	bzip2-devel
BuildRequires:	curl-devel
BuildRequires:	gmp-devel
BuildRequires:	libidn-devel
BuildRequires:	ncurses-devel
BuildRequires:	zlib-devel
Requires:	bzip2-libs
Requires:	curl
Requires:	qmail-toaster
Requires:	gmp
Requires:	libidn
Requires:	zlib
Obsoletes:	clamav-toaster
BuildRoot:      %{_topdir}/BUILDROOT/%{name}-%{version}-%{release}.%{_arch}

%define debug_package %{nil}
%define _initpath     /etc/rc.d/init.d
%define _qdir         /var/qmail
%define _qtlogdir     /var/log/qmail
%define _spath        %{_qdir}/supervise
%define ccflags       %{optflags}
%define ldflags       %{optflags}

#-------------------------------------------------------------------------------
%description
#-------------------------------------------------------------------------------
Clam AntiVirus is a GPL anti-virus toolkit for UNIX. The main purpose of this
software is the integration with mail servers (attachment scanning).
The package provides a flexible and scalable multi-threaded daemon,
a command line scanner, and a tool for automatic updating via Internet.
The programs are based on a shared library distributed with package,
which you can use with your own software.
Most importantly, the virus database is kept up to date .

#-------------------------------------------------------------------------------
%prep
#-------------------------------------------------------------------------------
%setup -q

# Patch the config files
%patch0 -p1

#-------------------------------------------------------------------------------
%build
#-------------------------------------------------------------------------------

# Run configure to create makefile
#-------------------------------------------------------------------------------
#%{__aclocal}
#%{__autoconf}
#%{__automake}
%configure \
      --disable-clamav

# shubes 9/27/13 - added per http://fedoraproject.org/wiki/RPath_Packaging_Draft
sed -i 's|^hardcode_libdir_flag_spec=.*|hardcode_libdir_flag_spec=""|g' libtool
sed -i 's|^runpath_var=LD_RUN_PATH|runpath_var=DIE_RPATH_DIE|g' libtool

%{__make}

#-------------------------------------------------------------------------------
%install
#-------------------------------------------------------------------------------
rm -rf %{buildroot}
install -d %{buildroot}%{_initpath}/
install -d %{buildroot}%{_sysconfdir}/cron.daily
install -d %{buildroot}%{_sysconfdir}/logrotate.d
install -d %{buildroot}/var/log/clamav
install -d %{buildroot}/var/run/clamav
install -d %{buildroot}/var/spool/clamav

%{__make} DESTDIR=%{buildroot} install

install -d %{buildroot}%{_qdir}
install -d %{buildroot}%{_spath}
install -d %{buildroot}%{_spath}/clamd
install -d %{buildroot}%{_spath}/clamd/log
install -d %{buildroot}%{_spath}/clamd/supervise
install -d %{buildroot}%{_datadir}/clamav
install -d %{buildroot}/var/log/qmail
install -d %{buildroot}/var/log/qmail/clamd

rm -rf %{buildroot}%{_mandir}/man8/clamav-milter.8*
install etc/clamd.conf.sample     %{buildroot}%{_sysconfdir}/clamd.conf
install etc/freshclam.conf.sample %{buildroot}%{_sysconfdir}/freshclam.conf.sample
touch               %{buildroot}%{_sysconfdir}/freshclam.conf

install freshclam.logrotate   %{buildroot}%{_sysconfdir}/logrotate.d/freshclam
install freshclam.init        %{buildroot}%{_initpath}/freshclam
install clamav.run.supervise  %{buildroot}%{_spath}/clamd/run
install clamav.log.supervise  %{buildroot}%{_spath}/clamd/log/run

touch %{buildroot}/var/log/clamav/freshclam.log
touch %{buildroot}%{_datadir}/clamav/main.cvd
touch %{buildroot}%{_datadir}/clamav/daily.cvd
touch %{buildroot}%{_datadir}/clamav/bytecode.cvd

# Make freshclam sym link
#-------------------------------------------------------------------------------
pushd %{buildroot}%{_bindir}
  ln -s ../..%{_initpath}/freshclam fclamctl
popd

#-------------------------------------------------------------------------------
%clean
#-------------------------------------------------------------------------------
rm -rf %{buildroot}

#-------------------------------------------------------------------------------
%pre
#-------------------------------------------------------------------------------
if [ -z "`/usr/bin/id -g clamav 2>/dev/null`" ]; then
	/usr/sbin/groupadd -g 46 -r clamav 2>&1 || :
fi
if [ -z "`/usr/bin/id -u clamav 2>/dev/null`" ]; then
	/usr/sbin/useradd -u 46 -r -M -d /tmp  -s /sbin/nologin -c "Clam AntiVirus" -g clamav clamav 2>&1 || :
fi

# need to kill freshclam here if it's running
# but only if we're not installing in a sandbox.
if [ ! -f /boot/.qtp-sandbox ]; then
  killall -TERM freshclam > /dev/null 2>&1 || :
fi

#-------------------------------------------------------------------------------
%post
#-------------------------------------------------------------------------------

# Remove old/duplicate database files if they exist
# Note, as best as I can tell, database files are downloaded as .cvd files,
# but once freshclam updates them, they're converted to .cld files.
datadir=/usr/share/clamav
for oldfile in daily.inc main.inc; do
  if [ -e $datadir/$oldfile ]; then
    rm -rf $datadir/$oldfile
  fi
done
for dupfile in bytecode daily main; do
  if [ -e $datadir/$dupfile.cld ] && [ -e $datadir/$dupfile.cvd ]; then
    rm -f $datadir/$dupfile.cvd
  fi
done

# Use country mirror for virus DB
ZONES="/usr/share/zoneinfo/zone.tab"
CONFIG="/etc/sysconfig/clock"

if [ -r "$CONFIG" -a -r "$ZONES" ]; then
  source "$CONFIG"
  export CODE="$(grep -E "\b$ZONE\b" "$ZONES" | head -1 | cut -f1 | tr [A-Z] [a-z])"
fi

if [ -z "$CODE" ]; then
  export CODE="local"
fi

sed -e "s%^#DatabaseMirror .*%DatabaseMirror db.$CODE.clamav.net%" \
      %{_sysconfdir}/freshclam.conf.sample \
     >%{_sysconfdir}/freshclam.conf

if [ -f %{_sysconfdir}/freshclam.conf.sample.rpmnew ]; then
  sed -e "s%^#DatabaseMirror .*%DatabaseMirror db.$CODE.clamav.net%" \
        %{_sysconfdir}/freshclam.conf.sample.rpmnew \
       >%{_sysconfdir}/freshclam.conf.rpmnew
fi

/sbin/chkconfig --add freshclam  
/sbin/chkconfig freshclam on

# if we're installing in a sandbox, then
#   touch the database files so that simscan will build
# otherwise
#   run freshclam to get/update definition files
#   start freshclam daemon
if [ -f /boot/.qtp-sandbox ]; then
  mkdir -p %{_datadir}/clamav
  touch %{_datadir}/clamav/main.cvd
  touch %{_datadir}/clamav/daily.cvd
  touch %{_datadir}/clamav/bytecode.cvd
else
  freshclam
  /sbin/service freshclam start > /dev/null 2>&1
fi

#-------------------------------------------------------------------------------
%preun
#-------------------------------------------------------------------------------
if [ $1 -eq 0 ]; then
  userdel clamav

  /sbin/chkconfig --del freshclam 

  # Remove runlevel links
  rm -f %{_sysconfdir}/rc0.d/K30freshclam 2>&1 > /dev/null
  rm -f %{_sysconfdir}/rc1.d/K30freshclam 2>&1 > /dev/null
  rm -f %{_sysconfdir}/rc2.d/S80freshclam 2>&1 > /dev/null
  rm -f %{_sysconfdir}/rc3.d/S80freshclam 2>&1 > /dev/null
  rm -f %{_sysconfdir}/rc4.d/S80freshclam 2>&1 > /dev/null
  rm -f %{_sysconfdir}/rc5.d/S80freshclam 2>&1 > /dev/null
  rm -f %{_sysconfdir}/rc6.d/K30freshclam 2>&1 > /dev/null
fi

#-------------------------------------------------------------------------------
%postun
#-------------------------------------------------------------------------------
if [ $1 = "0" ]; then
  rm -fR %{_spath}/clamd/
  rm -fR %{_qtlogdir}/clamd/
fi

#-------------------------------------------------------------------------------
# triggerin is executed after clamav is installed, if simscan is installed
# *and* after simscan is installed while clamav is installed
#-------------------------------------------------------------------------------
%triggerin -- simscan-toaster
#-------------------------------------------------------------------------------
if [ -x /var/qmail/bin/update-simscan ]; then
  /var/qmail/bin/update-simscan
fi

#-------------------------------------------------------------------------------
%files 
#-------------------------------------------------------------------------------
%defattr(0644,root,root,0755)

# Dirs
%attr(0755,clamav,clamav) %dir /var/log/clamav
%attr(0755,clamav,clamav) %dir /var/run/clamav
%attr(0755,root,qmail)    %dir %{_qdir}
%attr(0755,qmaill,qmail)  %dir %{_spath}
%attr(1700,qmaill,qmail)  %dir %{_spath}/clamd
%attr(0700,qmaill,qmail)  %dir %{_spath}/clamd/log
%attr(0755,qmaill,qmail)  %dir %{_spath}/clamd/supervise
%attr(0700,qmaill,qmail)  %dir /var/log/qmail
%attr(0755,qmaill,qmail)  %dir /var/log/qmail/clamd
%attr(0755,clamav,clamav) %dir %{_datadir}/clamav

# Executables
%attr(0755,root,root) %{_bindir}/clamscan
%attr(0755,root,root) %{_bindir}/clamdscan
%attr(0755,root,root) %{_bindir}/freshclam
%attr(0755,root,root) %{_bindir}/clamdtop
%attr(0755,root,root) %{_bindir}/clamav-config
%attr(0755,root,root) %{_bindir}/clamconf
%attr(0755,root,root) %{_bindir}/sigtool
%attr(0755,root,root) %{_bindir}/clambc
%attr(0755,root,root) %{_sbindir}/clamd
%attr(0755,root,root) %{_initpath}/freshclam
%attr(0751,qmaill,qmail) %{_spath}/clamd/run
%attr(0751,qmaill,qmail) %{_spath}/clamd/log/run

# Sym Link
%attr(-,root,root) %{_bindir}/fclamctl

# Configuration
%attr(0644,root,clamav) %config            %{_sysconfdir}/clamd.conf.sample
%attr(0644,root,clamav) %config(noreplace) %{_sysconfdir}/clamd.conf
%attr(0640,root,clamav) %config            %{_sysconfdir}/freshclam.conf.sample
%attr(0640,root,clamav) %ghost             %{_sysconfdir}/freshclam.conf
%attr(0644,root,root)   %config(noreplace) %{_sysconfdir}/logrotate.d/freshclam

# Data
%attr(0640,clamav,clamav) %ghost /var/log/clamav/freshclam.log
# These will be fetched by freshclam beginning with 0.97.5-1.4.1
%attr(0644,clamav,clamav) %ghost %{_datadir}/clamav/main.cvd
%attr(0644,clamav,clamav) %ghost %{_datadir}/clamav/daily.cvd
%attr(0644,clamav,clamav) %ghost %{_datadir}/clamav/bytecode.cvd

# Devel
%attr(0644,root,root) %{_includedir}/clamav.h
%attr(0755,root,root) %{_libdir}/libclamav.so.*
%attr(0755,root,root) %{_libdir}/libclamav.so
%attr(0755,root,root) %{_libdir}/libclamav.la
%attr(0755,root,root) %{_libdir}/libclamunrar*
%attr(0644,root,root) %{_libdir}/pkgconfig/libclamav.pc

# Documents
%doc AUTHORS BUGS COPYING ChangeLog FAQ INSTALL NEWS README
%doc docs/*.pdf test/

# Man pages
%{_mandir}/man1/*
%{_mandir}/man5/*
%{_mandir}/man8/clamd.8*

#-------------------------------------------------------------------------------
%changelog
#-------------------------------------------------------------------------------
* Fri Nov 15 2013 Eric Shubert <eric@datamatters.us> 0.98-0.qt
- Migrated to repoforge
- Removed -toaster designation
- Added CentOS 6 support
- Removed unsupported cruft
* Wed Sep 25 2013 Eric Shubert <eric@datamatters.us> 0.98-1.4.5
- Updated clamav sources to 0.98
- Fixed removal of old .cvd files and .inc directories.
- Changed freshclam.conf.dist to freshclam.conf.sample (like upstream now)
* Sun Apr 28 2013 Eric Broch <ebroch@whitehorsetc.com> 0.97.8-1.4.4
- Updated clamav sources to 0.97.8
* Fri Mar 15 2013 Eric Shubert <eric@datamatters.us> 0.97.7-1.4.3
- Updated clamav sources to 0.97.7
* Tue Sep 18 2012 Eric Shubert <eric@datamatters.us> 0.97.6-1.4.2
- Updated clamav sources to 0.97.6
* Fri Jun 15 2012 Eric Shubert <eric@datamatters.us> 0.97.5-1.4.1
- Updated clamav sources to 0.97.5
- Modified patch for --fuzz=0 (default in COS6)
- Removed cld files
- Changed cvd files to %ghost, invoke freshclam to get/update them in %post
- Added bytecode.cvd
* Mon Mar 19 2012 Eric Shubert <ejs@shubes.net> 0.97.4-1.4.0
- Updated clamav sources to 0.97.4, bumped version to 1.4.0
- Modified patch for freshclam.conf to run update-simscan script
- Added %triggerin to run update-simscan script when clam/simscan are updated
- Cleaned up freshclam starting/stopping
- Fixed removal of old daily.cld, main.cld files
- Fixed the way that freshclam.conf is being created/updated with local mirro
- Removed (noreplace) from daily.cvd, main.cvd files
- Changed logrotate.d/freshclam file to config(noreplace)
* Tue Nov 08 2011 Jake Vickers <jake@qmailtoaster.com> 0.97.3-1.3.44
- Updated clamav sources to 0.97.3
* Fri Jul 29 2011 Jake Vickers <jake@qmailtoaster.com> 0.97.2-1.3.43
- updated clamav sources to 0.97.2
* Sun Jun 12 2011 Jake Vickers <jake@qmailtoaster.com> 0.97.1-1.3.42
- Updated clamav sources to 0.97.1
* Sat Feb 12 2011 Jake Vickers <jake@qmailtoaster.com> 0.97.0-1.3.41
- Updated clamav to 0.97.0
- Added a routine to remove old .cld file if it exists
* Fri Dec 03 2010 Jake Vickers <jake@qmailtoaster.com> 0.96.5-1.3.40
- Updated clamav to 0.96.5
- Re-diff'ed the patch file and renamed to mark a demarcation point
- Merged the freshclam patch into the clamav-qmailtoaster patch
* Tue Oct 26 2010 Jake Vickers <jake@qmailtoaster.com> 0.96.4-1.3.39
- Updated clamav to 0.96.4
- Version numbers for packaging got messed up at some point in the spec
- file comments - went back and changed the last couple of releases,
- but not going back past the 0.96 mark
* Tue Sep 21 2010 Jake Vickers <jake@qmailtoaster.com> 0.96.3-1.3.38
- Updated clamav to 0.96.3
* Sat Aug 14 2010 Jake Vickers <jake@qmailtoaster.com> 0.96.2-1.3.37
- Updated clamav to 0.96.2
* Fri May 28 2010 Jake Vickers <jake@qmailtoaster.com> 0.96.1-1.3.36
- Updated clamav to 0.96.1
* Sat Apr 10 2010 Jake Vickers <jake@qmailtoaster.com> 0.96.0-1.3.35
- Added patch file to adjust the freshclam.conf file settings
* Tue Apr 06 2010 Jake Vickers <jake@qmailtoaster.com> 0.96.0-1.3.33
- Updated clamav source to 0.96 (added .0 to align with current numbering)
- clambc added to 0.96.0
- libclamav.a removed from 0.96.0
- Updated patch file for clamd.conf to enable new settings and generally freshen up
* Sun Dec 06 2009 Jake Vickers <jake@qmailtoaster.com> 0.95.3-1.3.32
- Added Fedora 12 and Fedora 12 x86_64 support
* Mon Nov 16 2009 Jake Vickers <jake@qmailtoaster.com> 0.95.3-1.3.32
- Changed spec file to require libgmp-devel instead of libgmp3-devel
- for Mandriva 2009 and 2010 support
- Added Mandriva 2010 support
* Wed Oct 28 2009 Jake Vickers <jake@qmailtoaster.com> 0.95.3-1.3.31
- Updated clamav to 0.95.3 - bugfix release
* Tue Aug 18 2009 Eric Shubert <ejs@shubes.net> 0.95.2-1.3.30
- Modified %post to not do freshclam processing when installing in sandbox
* Fri Jun 12 2009 Jake Vickers <jake@qmailtoaster.com> 0.95.2-1.3.29
- Added Fedora 11 support
- Added Fedora 11 x86_64 support
* Wed Jun 10 2009 Jake Vickers <jake@qmailtoaster.com> 0.95.2-1.3.29
- Updated ClamAV to 0.95.2
- Added Mandriva 2009 support
* Thu Apr 23 2009 Jake Vickers <jake@qmailtoaster.com> 0.95.1-1.3.28
- Added Fedora 9 x86_64 and Fedors 10 x86_64 support
- Fixed typo that may have caused Fedora 10 to incorrectly build
* Thu Apr 16 2009 Jake Vickers <jake@qmailtoaster.com> 0.95.1-1.3.27
- Upgraded to ClamAV 0.95.1
* Wed Apr 01 2009 Jake Vickers <jake@qmailtoaster.com> 0.95.0-1.3.26
- Added clamdtop to the spec file and ncurses-devel dependency
* Tue Mar 31 2009 Jake Vickers <jake@qmailtoaster.com> 0.95.0-1.3.25
- Updated clamav to 0.95
* Mon Feb 16 2009 Jake Vickers <jake@qmailtoaster.com> 0.94.2-1.3.24
- Added Suse 11.1 support
* Mon Feb 09 2009 Jake Vickers <jake@qmailtoaster.com> 0.94.2-1.3.24
- Added Fedora 9 and 10 support
* Thu Dec 04 2008 Jake Vickers <jake@v2gnu.com> 0.94.2-1.3.23
- Upgraded to ClamAV 0.94.2
* Wed Nov 12 2008 Erik A. Espinoza <espinoza@kabewm.com> 0.94.1-1.3.22
- Upgraded to ClamAV 0.94.1
* Wed Sep 03 2008 Erik A. Espinoza <espinoza@kabewm.com> 0.94-1.3.21
- Upgraded to ClamAV 0.94
* Fri Jul 11 2008 Erik A. Espinoza <espinoza@kabewm.com> 0.93.3-1.3.20
- Upgraded to ClamAV 0.93.3
* Sun Jul 06 2008 Erik A. Espinoza <espinoza@kabewm.com> 0.93.1-1.3.19
- Upgraded to ClamAV 0.93.1
* Sun Apr 19 2008 Erik A. Espinoza <espinoza@kabewm.com> 0.93-1.3.18
- Upgraded to ClamAV 0.93
* Thu Feb 20 2008 Erik A. Espinoza <espinoza@kabewm.com> 0.92.1-1.3.17
- Upgraded to ClamAv 0.92.1
* Tue Dec 25 2007 Erik A. Espinoza <espinoza@kabewm.com> 0.92-1.3.16
- Upgraded to ClamAV 0.92
* Sun Aug 26 2007 Erik A. Espinoza <espinoza@kabewm.com> 0.91.2-1.3.15
- Upgraded to ClamAV 0.91.2
* Tue Jul 17 2007 Erik A. Espinoza <espinoza@kabewm.com> 0.91.1-1.3.14
- Upgraded to ClamAV 0.91.1
* Sun Jun 03 2007 Erik A. Espinoza <espinoza@kabewm.com> 0.90.3-1.3.13
- Upgraded to ClamAV 0.90.3
* Sat Apr 14 2007 Nick Hemmesch <nick@ndhsoft.com> 0.90.2-1.3.12
- Upgraded to ClamAV 0.90.2
- Added CentOS 5 i386 support
- Added CentOS 5 x86_64 support
* Fri Mar 02 2007 Erik A. Espinoza <espinoza@kabewm.com> 0.90.1-1.3.11
- Upgraded to ClamAV 0.90.1
- Removed stderr patch
- Removed logging configuration from default config
* Wed Feb 14 2007 Erik A. Espinoza <espinoza@kabewm.com> 0.90-1.3.10
- Updated to ClamAV 0.90 release
* Thu Feb 01 2007 Erik A. Espinoza <espinoza@kabewm.com> 0.90rc3-1.3.9
- Updated to ClamAV 0.90rc3
- Set FixStaleSocket to yes in clamd.conf default
* Sun Nov 05 2006 Erik A. Espinoza <espinoza@forcenetworks.com> 0.90rc2-1.3.8
- Removed freshclam cron, as it breaks new ClamAV
* Thu Nov 02 2006 Erik A. Espinoza <espinoza@forcenetworks.com> 0.90rc2-1.3.7
- Added Fedora Core 6 support
* Mon Oct 30 2006 Erik A. Espinoza <espinoza@forcenetworks.com> 0.90rc2-1.3.6
- Upgraded to ClamAV 0.90rc2 w/ Experimental settings enabled
* Sun Oct 21 2006 Erik A. Espinoza <espinoza@forcenetworks.com> 0.90RC1.1-1.3.5
- Upgraded to ClamAV 0.90RC1.1 w/ Experimental settings enabled
* Sun Oct 15 2006 Erik A. Espinoza <espinoza@forcenetworks.com> 0.88.5-1.3.4
- Upgraded to ClamAV 0.88.5
* Mon Aug 07 2006 Erik A. Espinoza <espinoza@forcenetworks.com> 0.88.4-1.3.3
- Upgraded to ClamAV 0.88.4
* Sun Jul 02 2006 Erik A. Espinoza <espinoza@forcenetworks.com> 0.88.3-1.3.2
- Upgraded to ClamAV 0.88.3
* Mon Jun 05 2006 Nick Hemmesch <nick@ndhsoft.com> 0.87.1-1.3.1
- Added SuSE 10.1 support
* Sat May 13 2006 Nick Hemmesch <nick@ndhsoft.com> 0.87.1-1.2.15
- Added Fedora Core 5 support
* Wed May 03 2006 Erik A. Espinoza <espinoza@forcenetworks.com> 0.88.2-1.2.14
- Fixed freshclam logrotate
- Add new freshclam init script 
- Upgraded to ClamAV 0.88.2
* Sun Apr 30 2006 Nick Hemmesch <nick@ndhsoft.com> 0.87.1-1.2.13
- Fixed freshclam logrotate thanks to xspace
* Thu Apr 06 2006 Erik A. Espinoza <espinoza@forcenetworks.com> 0.88.1-1.2.12
- Upgraded to ClamAV 0.88.1
* Thu Jan 12 2006 Erik A. Espinoza <espinoza@forcenetworks.com> 0.88-1.2.11
- Upgraded to ClamAV 0.88
* Sun Nov 20 2005 Nick Hemmesch <nick@ndhsoft.com> 0.87.1-1.2.10
- Add SuSE 10.0 and Mandriva 2006.0 support
* Thu Nov 10 2005 Erik A. Espinoza <espinoza@forcenetworks.com> 0.87.1-1.2.9
- Upgraded to 0.87.1
* Sat Oct 15 2005 Nick Hemmesch <nick@ndhsoft.com> 0.87-1.2.8
- Add Fedora Core 4 x86_64 support
* Sat Oct 01 2005 Nick Hemmesch <nick@ndhsoft.com> 0.87-1.2.7
- Add CentOS 4 x86_64 support
* Tue Sep 20 2005 Erik A. Espinoza <espinoza@forcenetworks.com> 0.87-1.2.6
- Upgraded to clamav 0.87
- Changed zlib to require 1.2.3
* Mon Jul 25 2005 Erik A. Espinoza <espinoza@forcenetworks.com> 0.86.2-1.2.5
- Upgraded to clamav 0.86.2
* Fri Jul 01 2005 Nick Hemmesch <nick@ndhsoft.com> 0.86.1-1.2.4
- Add support for Fedora Core 4
* Sun Jun 26 2005 Nick Hemmesch <nick@ndhsoft.com> 0.86.1-1.2.3
- Update to clamav-0.86.1
* Fri Jun 03 2005 Torbjorn Turpeinen <tobbe@nyvalls.se> 0.85-1.2.2
- Gnu/Linux Mandrake 10.0,10.1,10.2 support
- fix deps and conditional %%multiarch for 10.2
* Sun May 22 2005 Nick Hemmesch <nick@ndhsoft.com> 0.85.1-1.2.1
- Adapt ClamAV for QmailToaster
- Initial build
