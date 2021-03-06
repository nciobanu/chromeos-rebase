import sqlite3
import os
from config import rebasedb, topiclist

def get_topic(file):
    for (subdir, topic, ) in topics:
        if file.startswith(subdir):
	    return topic
    return 0

conn = sqlite3.connect(rebasedb)
c = conn.cursor()

def update_sha(sha, topic, file="", base=""):
  filelist = [(sha, topic, file, base)]
  count = 0
  while filelist:
    (sha, topic, file, base) = filelist.pop(0)
    c.execute("select disposition, topic from commits where sha is '%s' order by date" % (sha))
    result = c.fetchone()
    if result:
        if result[0] == 'drop':
	    # print "Disposition for '%s' is '%s', skipping" % (sha, result[0])
	    return 0
        if result[1] != 0:
	    if result[1] != topic:
		if file != "":
		    print "topic already set to %d for sha '%s' [%s], skipping" % (result[1], sha, file)
		else:
		    print "topic already set to %d for sha '%s' [none], skipping" % (result[1], sha)
	    return 0
    else:
        print "No entry for sha '%s' found in database" % sha
        return 0
    print "  Adding sha '%s' to topic %d [%s]" % (sha, topic, file)
    c.execute("UPDATE commits SET topic=%d where sha='%s'" % (topic, sha))
    count = count + 1
    # print "Attached SHA '%s' to topic %d" % (sha, topic)
    # Attach all SHAs touching the same set of files to the same topic.
    c.execute("select filename from files where sha is '%s'" % (sha))
    for (filename,) in c.fetchall():
        c.execute("select sha from files where filename is '%s'" % (filename))
        for (fsha,) in c.fetchall():
	    # print "Expect to attach sha '%s' to topic %d, file='%s'" % (fsha, topic, filename)
	    if fsha != sha and not filename.endswith('Makefile') and not filename.endswith('Kconfig'):
	        if base != "" and not filename.startswith(base) and get_topic(filename) != topic:
		    print "  Skipping '%s': base '%s' mismatch [%d-%d]" % (filename, base, topic, get_topic(filename))
		    continue
		filelist.append([fsha, topic, filename, base])
  return count

def handle_topic(topic, subdir):
    count = 0
    print "Handling topic %d, subdirectory/file '%s'" % (topic, subdir)
    c.execute("select sha, filename from files where filename like '%s%%'" % subdir)
    for (sha, filename,) in c.fetchall():
        if filename.startswith(subdir):
	    count = count + update_sha(sha, topic, filename, subdir)
    print "Topic %d (%s): %d entries" % (topic, subdir, count)

c.execute("select sha from commits order by date")
for (sha,) in c.fetchall():
    c.execute("UPDATE commits SET topic=0 where sha='%s'" % sha)

topic = 1
topics = [ ]
for subdirs in topiclist:
    for subdir in subdirs:
	topics.append((subdir, topic))
    topic = topic + 1

for (subdir, topic, ) in topics:
    handle_topic(topic, subdir)

topic = topic + 1

while True:
    print "Topic %d" % topic
    c.execute("select sha from commits where topic=0 and disposition <> 'drop' order by date")
    # c.execute("select sha from commits where topic=0 order by date")
    sha = c.fetchone()
    if sha:
	c.execute("select filename from files where sha is '%s'" % (sha[0]))
	files = c.fetchone()
	file=""
	subdir=""
	if files:
	    # Try to find a directory name outside include and Documentation
	    # asn use it as file and base (topic)
	    file = files[0] + '+'
	    subdir = os.path.dirname(files[0])
	    while files and (files[0].startswith('Documentation') or files[0].endswith('.h') or subdir == ""):
		files = c.fetchone()
		if files and not files[0].startswith('Documentation') and not files[0].endswith('.h') \
			and os.path.dirname(files[0]) != "":
		    file = files[0] + '+'
	            subdir = os.path.dirname(files[0])
	# Based on a sha, we found a file and subdirectory. Use it to attach
	# any matching SHAs to this subdirectory if the match is in a source
	# directory.
	#
	if subdir.startswith('include') or subdir.startswith('Documentation') or subdir=="":
            count = update_sha(sha[0], topic, file, subdir)
	    print "Topic %d [%s]: %d entries" % (topic, file, count)
	else:
	    topics.append((subdir, topic))
            handle_topic(topic, subdir)
    else:
        break
    topic = topic + 1

conn.commit()
conn.close()
