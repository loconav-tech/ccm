# downloaded sources handling
from __future__ import with_statement

import os, shutil, urllib2, tarfile, tempfile, subprocess
import common

ARCHIVE="http://archive.apache.org/dist/cassandra"

def setup(version, verbose=False):
    cdir = version_directory(version)
    if cdir is None:
        download_version(version, verbose=verbose)
        cdir = version_directory(version)
    return cdir

def validate(path):
    if path.startswith(__get_dir()):
        _, version = os.path.split(os.path.normpath(path))
        setup(version)

def download_version(version, url=None, verbose=False):
    u = "%s/%s/apache-cassandra-%s-src.tar.gz" % (ARCHIVE, version.split('-')[0], version) if url is None else url
    _, target = tempfile.mkstemp(suffix=".tar.gz", prefix="ccm-")
    try:
        __download(u, target, show_progress=verbose)
        if verbose:
            print "Extracting %s as version %s ..." % (target, version)
        tar = tarfile.open(target)
        dir = tar.next().name.split("/")[0]
        tar.extractall(path=__get_dir())
        tar.close()
        target_dir = os.path.join(__get_dir(), version)
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        shutil.move(os.path.join(__get_dir(), dir), target_dir)

        # compiling cassandra and the stress tool
        logfile = os.path.join(__get_dir(), "last.log")
        if verbose:
            print "Compiling Cassandra %s ..." % version
        with open(logfile, 'w') as lf:
            lf.write("--- Cassandra build -------------------\n")
            if subprocess.call(['ant', 'build'], cwd=target_dir, stdout=lf, stderr=lf) is not 0:
                raise common.CCMError("Error compiling Cassandra. See %s for details" % logfile)

            lf.write("\n\n--- cassandra/stress build ------------\n")
            stress_dir = os.path.join(target_dir, "tools", "stress") if version >= "0.8.0" else os.path.join(target_dir, "contrib", "stress")
            try:
                if subprocess.call(['ant', 'build'], cwd=stress_dir, stdout=lf, stderr=lf) is not 0:
                    raise common.CCMError("Error compiling Cassandra stress tool.  See %s for details (you will still be able to use ccm but not the stress related commands)" % logfile)
            except IOError as e:
                raise common.CCMError("Error compiling Cassandra stress tool: %s (you will still be able to use ccm but not the stress related commands)" % str(e))
    except urllib2.URLError as e:
        msg = "Invalid version %s" % version if url is None else "Invalid url %s" % url
        msg = msg + " (underlying error is: %s)" % str(e)
        raise common.ArgumentError(msg)
    except tarfile.ReadError as e:
        raise common.ArgumentError("Unable to uncompress downloaded file: %s" % str(e))

def version_directory(version):
    dir = os.path.join(__get_dir(), version)
    if os.path.exists(dir):
        try:
            common.validate_cassandra_dir(dir)
            return dir
        except common.ArgumentError as e:
            shutil.rmtree(dir)
            return None
    else:
        return None

def clean_all():
    shutil.rmtree(__get_dir())

def __download(url, target, show_progress=False):
    u = urllib2.urlopen(url)
    f = open(target, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    if show_progress:
        print "Downloading %s to %s (%.3fMB)" % (url, target, float(file_size) / (1024 * 1024))

    file_size_dl = 0
    block_sz = 8192
    status = None
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        if show_progress:
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = chr(8)*(len(status)+1) + status
            print status,

    if show_progress:
        print ""
    f.close()
    u.close()

def __get_dir():
    repo = os.path.join(common.get_default_path(), 'repository')
    if not os.path.exists(repo):
        os.mkdir(repo)
    return repo
